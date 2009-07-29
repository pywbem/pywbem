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

r"""Python CIM Providers (aka "nirvana")

This module is an abstraction and utility layer between a CIMOM and 
Python providers.  The CIMOM uses this module to load Python providers, 
and route requests to those providers.  

Python Provider Modules

    Python Providers are implemented as Python modules.  By convention
    these modules are installed into /usr/lib/pycim.  However, they can 
    be anywhere.  These modules are loaded on demand using load_source() 
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
    one or more subclasses of CIMProvider within the provider module, and
    registering instances of the subclass(es) with CIM class names by way 
    of the get_providers function (described below).  Refer to 
    the documentation for CIMProvider in this module. 

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
            CIMProvider subclasses.  Note that multiple classes can be 
            instrumented by the same instance of a CIMProvider subclass.  
            The CIM class names are case-insensitive, since this dict is
            converted to a NocaseDict. 

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
           
            For example, a Python Provider Module may contain the following:

                class Py_FooBarProvider(CIMProvider):
                    ...

                def get_providers(env):
                    _fbp = Py_FooBarProvider()
                    return {'Py_Foo':_fbp, 'Py_Bar':_fbp}

        get_initial_polling_interval(env):
            Return the number of seconds before the first call to poll.

            If this method returns zero, then the poll method is never called.

            Arguments: 
            env -- Provider Environment (pycimmb.ProviderEnvironment)

        poll(env):
            Do some work, and return the number of seconds until the next poll.

            A polled provider's poll function will be called periodically by 
            the CIMOM.  The polled provider can use this opportunity to do 
            some work, such as checking on some conditions, and generating
            indications.  The poll function returns the number of seconds the 
            CIMOM should wait before calling poll again.  A return value of -1
            indicates to the CIMOM that the previous poll value should be used. 
            A return value of 0 indicates that the poll function should never
            be called again. 

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)

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
            ns -- The namespace where the even occurred
            handler_instance -- 
            indication_instance -- The indication

        activate_filter (env, filter, ns, classes, 
                         first_activation):
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
            filter --
            namespace -- 
            classes -- 
            first_activation --

        deactivate_filter(env, filter, ns, classes, 
                          last_activation):
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
            filter --
            ns -- 
            classes -- 
            last_activation --

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
from imp import load_source
import types

__all__ = ['CIMProvider']


def _path_equals_ignore_host(lhs, rhs):
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


class CIMProvider(object):
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

    def get_instance (self, env, model, cim_class):
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
        cim_class -- The pywbem.CIMClass

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, unrecognized 
            or otherwise incorrect parameters)
        CIM_ERR_NOT_FOUND (the CIM Class does exist, but the requested CIM 
            Instance does not exist in the specified namespace)
        CIM_ERR_FAILED (some other unspecified error occurred)

        """
        return None

    def enum_instances(self, env, model, cim_class, keys_only):
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
        cim_class -- The pywbem.CIMClass
        keys_only -- A boolean.  True if only the key properties should be
            set on the generated instances.

        Possible Errors:
        CIM_ERR_FAILED (some other unspecified error occurred)

        """
        pass

    def set_instance(self, env, instance, previous_instance, cim_class):
        """Return a newly created or modified instance.

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        instance -- The new pywbem.CIMInstance.  If modifying an existing 
            instance, the properties on this instance have been filtered by 
            the PropertyList from the request.
        previous_instance -- The previous pywbem.CIMInstance if modifying 
            an existing instance.  None if creating a new instance. 
        cim_class -- The pywbem.CIMClass

        Return the new instance.  The keys must be set on the new instance. 

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_NOT_SUPPORTED
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, unrecognized 
            or otherwise incorrect parameters)
        CIM_ERR_ALREADY_EXISTS (the CIM Instance already exists -- only 
            valid if previous_instance is None, indicating that the operation
            was CreateInstance)
        CIM_ERR_NOT_FOUND (the CIM Instance does not exist -- only valid 
            if previous_instance is not None, indicating that the operation
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

    def references(self, env, object_name, model, assoc_class, 
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
        assoc_class -- The pywbem.CIMClass.
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
           |              |  [Association] assoc_class        |      |
           | object_name  |  ~~~~~~~~~~~~~~~~~~~~~~~~~        |      |
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
        pass

    def _set_filter_results(self, value):
        self._filter_results = value
    def _get_filter_results(self):
        if hasattr(self, '_filter_results'):
            return self._filter_results
        return True
    filter_results = property(_get_filter_results, 
                              _set_filter_results,
                              None,
        """Determines if the CIMProvider base class should filter results

        If True, the subclass of CIMProvider in the provider module
        does not need to filter returned results based on property_list, 
        and in the case of association providers, role, result_role, and 
        result_class_name.  The results will be filtered by the 
        CIMProvider base class. 

        If False, the CIMProvider base class will do no filtering. 
        Therefore the subclass of CIMProvider in the provider module will
        have to filter based on property_list, and in the case of 
        association providers, role, result_role, and result_class_name.""")

    def MI_enumInstanceNames(self, 
                             env, 
                             ns, 
                             cimClass):
        """Return instance names of a given CIM class

        Implements the WBEM operation EnumerateInstanceNames in terms 
        of the enum_instances method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_enumInstanceNames called...')
        provClass = False
        keys = pywbem.NocaseDict()
        [keys.__setitem__(p.name, p) for p in cimClass.properties.values()\
                if 'key' in p.qualifiers]
        
        _strip_quals(keys)
        path = pywbem.CIMInstanceName(classname=cimClass.classname, 
                                            namespace=ns)
        model = pywbem.CIMInstance(classname=cimClass.classname, 
                                   properties=keys,
                                   path=path)
        gen = self.enum_instances(env=env,
                                       model=model,
                                       cim_class=cimClass,
                                       keys_only=True)
        try:
            iter(gen)
        except TypeError:
            logger.log_debug('CIMProvider MI_enumInstanceNames returning')
            return

        for inst in gen:
            rval = build_instance_name(inst)
            yield rval
        logger.log_debug('CIMProvider MI_enumInstanceNames returning')
    
    def MI_enumInstances(self, 
                         env, 
                         ns, 
                         propertyList, 
                         requestedCimClass, 
                         cimClass):
        """Return instances of a given CIM class

        Implements the WBEM operation EnumerateInstances in terms 
        of the enum_instances method.  A derived class will not normally
        override this method. 

        """
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_enumInstances called...')
        keyNames = get_keys_from_class(cimClass)
        plist = None
        if propertyList is not None:
            lkns = [kn.lower() for kn in keyNames]
            props = pywbem.NocaseDict()
            plist = [s.lower() for s in propertyList]
            pklist = plist + lkns
            [props.__setitem__(p.name, p) for p in cimClass.properties.values() 
                    if p.name.lower() in pklist]
        else:
            props = cimClass.properties
        _strip_quals(props)
        path = pywbem.CIMInstanceName(classname=cimClass.classname, 
                                            namespace=ns)
        model = pywbem.CIMInstance(classname=cimClass.classname, properties=props,
                                   path=path)
        gen = self.enum_instances(env=env,
                                       model=model,
                                       cim_class=cimClass,
                                       keys_only=False)
        try:
            iter(gen)
        except TypeError:
            logger.log_debug('CIMProvider MI_enumInstances returning')
            return
        for inst in gen:
            inst.path = build_instance_name(inst, keyNames)
            if self.filter_results and plist is not None:
                inst = inst.copy()
                filter_instance(inst, plist)
            yield inst
        logger.log_debug('CIMProvider MI_enumInstances returning')

    def MI_getInstance(self, 
                       env, 
                       instanceName, 
                       propertyList, 
                       cimClass):
        """Return a specific CIM instance

        Implements the WBEM operation GetInstance in terms 
        of the get_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_getInstance called...')
        keyNames = get_keys_from_class(cimClass)
        plist = None
        if propertyList is not None:
            lkns = [kn.lower() for kn in keyNames]
            props = pywbem.NocaseDict()
            plist = [s.lower() for s in propertyList]
            pklist = plist + lkns
            [props.__setitem__(p.name, p) for p in cimClass.properties.values() 
                    if p.name.lower() in pklist]
        else:
            props = cimClass.properties
        _strip_quals(props)
        model = pywbem.CIMInstance(classname=instanceName.classname, 
                                   properties=props,
                                   path=instanceName)
        for k, v in instanceName.keybindings.items():
            type = cimClass.properties[k].type

            if type != 'reference':
                v = val = pywbem.tocimobj(type, v)
            model.__setitem__(k, pywbem.CIMProperty(name=k, type=type, 
                                    value=v))

        rval = self.get_instance(env=env,
                                       model=model,
                                       cim_class=cimClass)
        if self.filter_results:
            filter_instance(rval, plist)
        logger.log_debug('CIMProvider MI_getInstance returning')
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
        logger.log_debug('CIMProvider MI_createInstance called...')
        rval = None
        ch = env.get_cimom_handle()
        cimClass = ch.GetClass(instance.classname, 
                                 instance.path.namespace, 
                                 LocalOnly=False, 
                                 IncludeQualifiers=True)
        # CIMOM has already filled in default property values for 
        # props with default values, if values not supplied by client. 
        rval = self.set_instance(env=env,
                              instance=instance,
                              previous_instance=None,
                              cim_class=cimClass)
        rval = build_instance_name(rval, cimClass)
        logger.log_debug('CIMProvider MI_createInstance returning')
        return rval

    def MI_modifyInstance(self, 
                          env, 
                          modifiedInstance, 
                          previousInstance, 
                          propertyList, 
                          cimClass):
        """Modify a CIM instance

        Implements the WBEM operation ModifyInstance in terms 
        of the set_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_modifyInstance called...')
        if propertyList is not None:
            plist = [p.lower() for p in propertyList]
            filter_instance(modifiedInstance, plist)
            modifiedInstance.update(modifiedInstance.path)
        self.set_instance(env=env,
                              instance=modifiedInstance,
                              previous_instance=previousInstance,
                              cim_class=cimClass)
        logger.log_debug('CIMProvider MI_modifyInstance returning')
    
    def MI_deleteInstance(self, 
                          env, 
                          instanceName):
        """Delete a CIM instance

        Implements the WBEM operation DeleteInstance in terms 
        of the delete_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_deleteInstance called...')
        self.delete_instance(env=env, instance_name=instanceName)
        logger.log_debug('CIMProvider MI_deleteInstance returning')


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
        logger.log_debug('CIMProvider MI_associators called. assocClass: %s' % (assocClassName))
        ch = env.get_cimom_handle()
        if not assocClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty assocClassName passed to Associators")
        assocClass = ch.GetClass(assocClassName, objectName.namespace, 
                                 LocalOnly=False, 
                                 IncludeQualifiers=True)
        plist = pywbem.NocaseDict()
        [plist.__setitem__(p.name, p) for p in assocClass.properties.values() 
                if 'key' in p.qualifiers or p.type == 'reference']
        _strip_quals(plist)
        model = pywbem.CIMInstance(classname=assocClass.classname, 
                                   properties=plist)
        model.path = pywbem.CIMInstanceName(classname=assocClass.classname, 
                                            namespace=objectName.namespace)
        for inst in self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    assoc_class=assocClass,
                                    result_class_name=resultClassName, 
                                    role=role, 
                                    result_role=None,
                                    keys_only=False):
            for prop in inst.properties.values():
                lpname = prop.name.lower()
                if prop.type != 'reference':
                    continue
                if role and role.lower() == lpname:
                    continue
                if resultRole and resultRole.lower() != lpname:
                    continue
                if _path_equals_ignore_host(prop.value, objectName):
                    continue
                if resultClassName and self.filter_results and \
                        not pywbem.is_subclass(ch, objectName.namespace, 
                                        sub=prop.value.classname, 
                                        super=resultClassName):
                    continue
                try:
                    if prop.value.namespace is None:
                        prop.value.namespace = objectName.namespace
                    inst = ch.GetInstance(prop.value, 
                                          IncludeQualifiers=True,
                                          IncludeClassOrigin=True,
                                          PropertyList=propertyList)
                except pywbem.CIMError, (num, msg):
                    if num == pywbem.CIM_ERR_NOT_FOUND:
                        continue
                    else:
                        raise
                if inst.path is None:
                    inst.path = prop.value
                yield inst
        logger.log_debug('CIMProvider MI_associators returning')

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
        logger.log_debug('CIMProvider MI_associatorNames called. assocClass: %s' % (assocClassName))
        ch = env.get_cimom_handle()
        if not assocClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty assocClassName passed to AssociatorNames")
        assocClass = ch.GetClass(assocClassName, objectName.namespace, 
                                 LocalOnly=False, 
                                 IncludeQualifiers=True)
        keys = pywbem.NocaseDict()
        [keys.__setitem__(p.name, p) for p in assocClass.properties.values() 
                if 'key' in p.qualifiers or p.type == 'reference' ]
        _strip_quals(keys)
        model = pywbem.CIMInstance(classname=assocClass.classname, 
                                   properties=keys)
        model.path = pywbem.CIMInstanceName(classname=assocClass.classname, 
                                            namespace=objectName.namespace)
        for inst in self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    assoc_class=assocClass,
                                    result_class_name=resultClassName, 
                                    role=role, 
                                    result_role=None,
                                    keys_only=False):
            for prop in inst.properties.values():
                lpname = prop.name.lower()
                if prop.type != 'reference':
                    continue
                if role and role.lower() == lpname:
                    continue
                if resultRole and resultRole.lower() != lpname:
                    continue
                if _path_equals_ignore_host(prop.value, objectName):
                    continue
                if resultClassName and self.filter_results and \
                        not pywbem.is_subclass(ch, objectName.namespace, 
                                        sub=prop.value.classname, 
                                        super=resultClassName):
                    continue
                if prop.value.namespace is None:
                    prop.value.namespace = objectName.namespace
                yield prop.value
        logger.log_debug('CIMProvider MI_associatorNames returning')

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
        logger.log_debug('CIMProvider MI_references called. resultClass: %s' % (resultClassName))
        ch = env.get_cimom_handle()
        if not resultClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty resultClassName passed to References")
        assocClass = ch.GetClass(resultClassName, objectName.namespace, 
                                 LocalOnly=False, 
                                 IncludeQualifiers=True)
        keyNames = get_keys_from_class(assocClass)
        plist = None
        if propertyList is not None:
            lkns = [kn.lower() for kn in keyNames]
            props = pywbem.NocaseDict()
            plist = [s.lower() for s in propertyList] 
            pklist = plist + lkns
            [props.__setitem__(p.name, p) for p in \
                    assocClass.properties.values() \
                    if p.name.lower() in pklist]
        else:
            props = assocClass.properties
        _strip_quals(props)
        model = pywbem.CIMInstance(classname=assocClass.classname, 
                                   properties=props)
        model.path = pywbem.CIMInstanceName(classname=assocClass.classname, 
                                            namespace=objectName.namespace)
        #if role is None:
        #    raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
        #                          "** this shouldn't happen")
        if role:
            if role not in model.properties:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                                      "** this shouldn't happen")
            model[role] = objectName

        for inst in self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    assoc_class=assocClass,
                                    result_class_name='', 
                                    role=role, 
                                    result_role=None,
                                    keys_only=False):
            inst.path = build_instance_name(inst, keyNames)
            if self.filter_results and plist is not None:
                inst = inst.copy()
                filter_instance(inst, plist)
            for prop in inst.properties.values():
                if hasattr(prop.value, 'namespace') and prop.value.namespace is None:
                    prop.value.namespace = objectName.namespace
            yield inst
        logger.log_debug('CIMProvider MI_references returning')

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
        logger.log_debug('CIMProvider MI_referenceNames <2> called. resultClass: %s' % (resultClassName))
        ch = env.get_cimom_handle()
        if not resultClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty resultClassName passed to ReferenceNames")

        assocClass = ch.GetClass(resultClassName, objectName.namespace, 
                                 LocalOnly=False, 
                                 IncludeQualifiers=True)
        keys = pywbem.NocaseDict()
        keyNames = [p.name for p in assocClass.properties.values()
                    if 'key' in p.qualifiers]
        for keyName in keyNames:
            p = assocClass.properties[keyName]
            keys.__setitem__(p.name, p)
        _strip_quals(keys)
        model = pywbem.CIMInstance(classname=assocClass.classname, 
                                   properties=keys)
        model.path = pywbem.CIMInstanceName(classname=assocClass.classname, 
                                            namespace=objectName.namespace)
        #if role is None:
        #    raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
        #                          "** this shouldn't happen")
        if role:
            if role not in model.properties:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                                      "** this shouldn't happen")
            model[role] = objectName
        for inst in self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    assoc_class=assocClass,
                                    result_class_name='', 
                                    role=role, 
                                    result_role=None,
                                    keys_only=True):
            for prop in inst.properties.values():
                if hasattr(prop.value, 'namespace') and prop.value.namespace is None:
                    prop.value.namespace = objectName.namespace
            yield build_instance_name(inst, keyNames)
        logger.log_debug('CIMProvider MI_referenceNames returning')

    def MI_invokeMethod(self, env, objectName, metaMethod, inputParams):
        """Invoke an extrinsic method.

        Implements the InvokeMethod WBEM operation by calling the 
        method on a derived class called cim_method_<method_name>, 
        where <method_name> is the name of the CIM method, in all 
        lower case.  
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        objectName -- The InstanceName or ClassName of the object on 
        which the method is invoked.
        metaMethod -- The CIMMethod representing the method to be 
            invoked. 
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
        logger.log_debug('CIMProvider MI_invokeMethod called. method: %s:%s' \
                % (objectName.classname,metaMethod.name))
        lmethName = "cim_method_%s" % metaMethod.name.lower()
        if hasattr(self, lmethName) :
            method = getattr(self, lmethName)
            new_inputs = dict([('param_%s' % k.lower(), v) \
                            for k, v in inputParams.items()])
            (rval, outs) = method(env=env, object_name=objectName, 
                                  method=metaMethod, **new_inputs)

            def add_type(v, _tp):
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
                    tp = _tp
                else:
                    tp = pywbem.cimtype(v)
                return (tp, v)

            for k, v in outs.items():
                if hasattr(v, 'namespace') and v.namespace is None:
                    v.namespace = objectName.namespace
                outs[k] = add_type(v, metaMethod.parameters[k].type)
            rval = add_type(rval, metaMethod.return_type)
            rval = (rval, outs)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_METHOD_NOT_FOUND, 
                              "%s:%s"%(objectName.classname, metaMethod.name))
        logger.log_debug('CIMProvider MI_invokeMethod returning')
        return rval

def filter_instance(inst, plist):
    """Remove properties from an instance that aren't in the PropertyList
    
    inst -- The CIMInstance
    plist -- The property List, or None.  The list items must be all 
        lowercase.
        
    """

    if plist is not None:
        for pname in inst.properties.keys():
            if pname.lower() not in plist:
                del inst.properties[pname]

def get_keys_from_class(cc):
    """Return list of the key property names for a class """
    return [prop.name for prop in cc.properties.values() \
            if 'key' in prop.qualifiers]

def build_instance_name(inst, obj=None):
    """Return an instance name from an instance, and set instance.path """
    if obj is None:
        for _ in inst.properties.values():
            inst.path.keybindings.__setitem__(_.name, _.value)
        return inst.path
    if not isinstance(obj, list):
        return build_instance_name(inst, get_keys_from_class(obj))
    keys = {}
    for _ in obj:
        if _ not in inst.properties:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                                  "Instance of %s is missing key property %s" \
                                  %(inst.classname, _))
        keys[_] = inst[_]
    inst.path = pywbem.CIMInstanceName(classname=inst.classname, 
                                       keybindings=keys,
                                       namespace=inst.path.namespace,
                                       host=inst.path.host)
    return inst.path


def _strip_quals(props):
    for prop in props.values(): # remove all but key quals
        try:
            prop.qualifiers = pywbem.NocaseDict({'KEY': 
                    prop.qualifiers['KEY']})
        except KeyError:
            prop.qualifiers = pywbem.NocaseDict()


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

    code = '''"""Python Provider for %(classname)s

Instruments the CIM class %(classname)s

"""

import pywbem

class %(classname)sProvider(pywbem.CIMProvider):
    """Instrument the CIM class %(classname)s \n''' % mappings
    code+= format_desc(cc, 4)
    code+= '''
    """'''


    args = inspect.getargspec(CIMProvider.get_instance)[0]
    args = ', '.join(args)
    code+= '''

    def __init__ (self, env):
        logger = env.get_logger()
        logger.log_debug('Initializing provider %%s from %%s' \\
                %% (self.__class__.__name__, __file__))
        # If you will be filtering instances yourself according to 
        # property_list, role, result_role, and result_class_name 
        # parameters, set self.filter_results to False
        # self.filter_results = False

    def get_instance(%s):
        """%s"""
        
        logger = env.get_logger()
        logger.log_debug('Entering %%s.get_instance()' \\
                %% self.__class__.__name__)
        ''' % (args, CIMProvider.get_instance.__doc__ )
    keyProps = [p for p in cc.properties.values() \
                if 'key' in p.qualifiers]
    code+= '''
        ux = model.update_existing

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
        #line = "#ux(%s=%s) # TODO (type = %s) %s" % \
        #        (prop.name, type_hint(prop), type_str(prop), is_required(prop))
        line = "#ux(%s=%s) # TODO %s" % \
                (prop.name, type_hint(prop), is_required(prop))
        code+= '''
        %s''' % line

    args = inspect.getargspec(CIMProvider.enum_instances)[0]
    args = ', '.join(args)
    code+= '''
        return model

    def enum_instances(%s):
        """%s"""

        logger = env.get_logger()
        logger.log_debug('Entering %%s.enum_instances()' \\
                %% self.__class__.__name__)

        while False: # TODO more instances?
            # TODO fetch system resource
            # Key properties''' % (args, CIMProvider.enum_instances.__doc__)
    for kp in keyProps:
        if kp.name == 'CreationClassName':
            line = "model['%s'] = '%s'" % (kp.name, cc.classname)
        else:
            line = "#model['%s'] = # TODO (type = %s)" % \
                    (kp.name, type_str(kp))
        code+='''    
            %s''' % line
    code+='''
            if keys_only:
                yield model
            else:
                try:
                    yield self.get_instance(env, model, cim_class)
                except pywbem.CIMError, (num, msg):
                    if num not in (pywbem.CIM_ERR_NOT_FOUND, 
                                   pywbem.CIM_ERR_ACCESS_DENIED):
                        raise\n'''

    args = inspect.getargspec(CIMProvider.set_instance)[0]
    args = ', '.join(args)
    code+= '''
    def set_instance(%s):
        """%s"""

        logger = env.get_logger()
        logger.log_debug('Entering %%s.set_instance()' \\
                %% self.__class__.__name__)
        # TODO create or modify the instance
        raise pywbem.CIMError(pywbem.CIM_ERR_NOT_SUPPORTED) # Remove to implement
        return instance''' % (args, CIMProvider.set_instance.__doc__)

    args = inspect.getargspec(CIMProvider.delete_instance)[0]
    args = ', '.join(args)
    code+= '''

    def delete_instance(%s):
        """%s""" 

        logger = env.get_logger()
        logger.log_debug('Entering %%s.delete_instance()' \\
                %% self.__class__.__name__)

        # TODO delete the resource
        raise pywbem.CIMError(pywbem.CIM_ERR_NOT_SUPPORTED) # Remove to implement
        ''' % (args, CIMProvider.delete_instance.__doc__)
                
    for method in cc.methods.values():
        inParms = [ p for p in method.parameters.values() if \
                    'in' in p.qualifiers and p.qualifiers['in'].value ]
        outParms = [ p for p in method.parameters.values() if \
                    'out' in p.qualifiers and p.qualifiers['out'].value ]
        code+= '''
    def cim_method_%s(self, env, object_name, method''' % method.name.lower()
        for p in inParms:
            code+= ''',\n%sparam_%s''' % (''.rjust(len(method.name)+20),
                                                    p.name.lower())
        code+= '''):
        """Implements %s.%s()\n''' % (cc.classname, method.name)
        code+= format_desc(method, 8)

        code+= '''
        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        object_name -- A pywbem.CIMInstanceName or pywbem.CIMCLassName 
            specifying the object on which the method %s() 
            should be invoked.
        method -- A pywbem.CIMMethod representing the method meta-data'''\
                % method.name

        for p in inParms:
            code+= '''
        param_%s --  The input parameter %s (type %s) %s''' \
                    % (p.name.lower(), p.name, type_str(p, method.name), 
                       is_required(p))
            code+= format_desc(p, 12)

        code+='''

        Returns a two-tuple containing the return value (type %s)
        and a dictionary with the out-parameters

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
        out_params = {}''' % method.name.lower()

        for p in outParms:
            code+='''
        #out_params['%s'] = %s # TODO''' % (p.name.lower(), 
                type_hint(p, method.name))

        code+='''
        rval = None # TODO (type %s)
        return (rval, out_params)
        ''' % type_str(method)

    if isAssoc:
        args = inspect.getargspec(CIMProvider.references)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
    def references(%s):
        """%s"""

        logger = env.get_logger()
        logger.log_debug('Entering %%s.references()' \\
                %% self.__class__.__name__)
        ch = env.get_cimom_handle()
        # This is a common pattern.  YMMV''' % \
                (args, CIMProvider.references.__doc__)
        refprops = []
        for prop in cc.properties.values():
            if prop.reference_class is not None:
                refprops.append((prop.name, prop.reference_class))
        for refprop in refprops:
            code+= '''
        if (not role or role.lower() == '%(refpropnamel)s') and \\
           pywbem.is_subclass(ch, object_name.namespace, 
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

def get_providers(env): 
    %(classname_l)s_prov = %(classname)sProvider(env)  
    return {'%(classname)s': %(classname_l)s_prov} 
''' % mappings

    owtypes = ['1', 'Instance']
    pegtypes = ['2', 'Instance']
    if isAssoc:
        owtypes[0]+= ',3'
        owtypes[1]+= ', Associator'
        pegtypes[0]+= ',3'
        pegtypes[1]+= ', Associator'
    if cc.methods:
        owtypes[0]+= ',6'
        owtypes[1]+= ', Method'
        pegtypes[0]+= ',5'
        pegtypes[1]+= ', Method'
    mof ='''
// OpenWBEM Provider registration for %(classname)s
instance of OpenWBEM_PyProviderRegistration
{
    InstanceID = "<org:product:%(classname)s:unique_id>"; // TODO
    NamespaceNames = {"root/cimv2"}; // TODO
    ClassName = "%(classname)s"; 
    ProviderTypes = {%(owtypeNums)s};  // %(owtypeStrs)s
    ModulePath = "/usr/lib/pycim/%(classname)sProvider.py";  // TODO
}; 

// Pegasus Provider registration for %(classname)s
instance of PG_ProviderModule
{
    Name = "/usr/lib/pycim/%(classname)sProvider.py";
    InterfaceType = "Python";
    InterfaceVersion = "1.0.0";
    Location = "/usr/lib/pycim/%(classname)sProvider.py";
    UserContext = 2; // Requestor
    Vendor = "TODO"; // TODO
    Version = "1.0";
}; 
instance of PG_Provider
{
    Name = "%(classname)s"; 
    ProviderModuleName = "/usr/lib/pycim/%(classname)sProvider.py"; 
}; 
instance of PG_ProviderCapabilities
{
    CapabilityID = "%(classname)s";
    ProviderModuleName = "/usr/lib/pycim/%(classname)sProvider.py";
    ProviderName = "%(classname)s";
    ClassName = "%(classname)s";
    Namespaces = {"root/cimv2"}; // TODO
    ProviderType = {%(pegtypeNum)s}; // %(pegtypeStr)s
};\n''' % {'classname': cc.classname, 
            'owtypeNums': owtypes[0], 
            'owtypeStrs': owtypes[1],
            'pegtypeNum': pegtypes[0], 
            'pegtypeStr': pegtypes[1]}

                
    return code, mof

class ProviderProxy(object):
    """Wraps a provider module, and routes requests into the module """

    def __init__ (self, env, provid):
        if isinstance(provid, types.ModuleType):
            self.provmod = provid
            self.provid = provid.__name__
            self.filename = provid.__file__
        else:
            self.provid = provid
            # odd chars in a module name tend to break things
            provider_name = 'pyprovider_'
            for ch in provid:
                provider_name+= ch.isalnum() and ch or '_'
            # let providers import other providers in the same directory
            provdir = dirname(provid)
            if provdir not in sys.path:
                sys.path.append(provdir)
            # use full path in module name for uniqueness. 
            try: 
                self.provmod = load_source(provider_name, provid)
            except IOError, arg:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                        "Error loading provider %s: %s" % (provid, arg))
            self.filename = self.provmod.__file__
        self.provregs = {}
        if hasattr(self.provmod, 'init'):
            self.provmod.init(env)
        if hasattr(self.provmod, 'get_providers'):
            self.provregs = pywbem.NocaseDict(self.provmod.get_providers(env))

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
                    "No callable for %s:%s on provider %s"%(classname,
                                                            cname, 
                                                            self.provid))
        return callable

##############################################################################
# enumInstanceNames
##############################################################################
    def MI_enumInstanceNames (self, 
                              env,
                              ns,
                              cimClass):
        logger = env.get_logger()
        logger.log_debug('ProviderProxy MI_enumInstanceNames called...')
        for i in self._get_callable(cimClass.classname, 
                                    'MI_enumInstanceNames') \
                                            (env, ns, cimClass):
            yield i
        logger.log_debug('CIMProvider MI_enumInstanceNames returning')

##############################################################################
# enumInstances
##############################################################################
    def MI_enumInstances(self, 
                         env, 
                         ns, 
                         propertyList, 
                         requestedCimClass, 
                         cimClass):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_enumInstances called...')
        for i in self._get_callable(cimClass.classname, 'MI_enumInstances') \
                           (env, 
                            ns, 
                            propertyList, 
                            requestedCimClass, 
                            cimClass):
            yield i 
        logger.log_debug('CIMProvider MI_enumInstances returning')

##############################################################################
# getInstance
##############################################################################
    def MI_getInstance(self, 
                       env, 
                       instanceName, 
                       propertyList, 
                       cimClass):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_getInstance called...')
        rval = self._get_callable(cimClass.classname, 'MI_getInstance')  \
               (env, 
                instanceName, 
                propertyList, 
                cimClass)
        logger.log_debug('CIMProvider MI_getInstance returning')
        return rval

##############################################################################
# createInstance
##############################################################################
    def MI_createInstance(self, 
                          env, 
                          instance):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_createInstance called...')
        rval = self._get_callable(instance.classname, 'MI_createInstance')  \
                (env, instance)
        logger.log_debug('CIMProvider MI_createInstance returning')
        return rval

##############################################################################
# modifyInstance
##############################################################################
    def MI_modifyInstance(self, 
                          env, 
                          modifiedInstance, 
                          previousInstance, 
                          propertyList, 
                          cimClass):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_modifyInstance called...')
        self._get_callable(cimClass.classname, 'MI_modifyInstance')  \
                (env, modifiedInstance, previousInstance,
                 propertyList, cimClass)
        logger.log_debug('CIMProvider MI_modifyInstance returning')
    
##############################################################################
# deleteInstance
##############################################################################
    def MI_deleteInstance(self, 
                          env, 
                          instanceName):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_deleteInstance called...')
        self._get_callable(instanceName.classname, 'MI_deleteInstance')  \
                (env, instanceName)
        logger.log_debug('CIMProvider MI_deleteInstance returning')


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
        logger.log_debug('CIMProvider MI_associators called. assocClass: %s' % (assocClassName))
        cname = assocClassName
        for i in self._get_callable(cname, 'MI_associators')  \
                (env, objectName, assocClassName, resultClassName, 
                        role, resultRole, propertyList):
            yield i 
        logger.log_debug('CIMProvider MI_associators returning')

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
        logger.log_debug('CIMProvider MI_associatorNames called. assocClass: %s' % (assocClassName))
        cname = assocClassName
        for i in self._get_callable(cname, 'MI_associatorNames')  \
                (env, objectName, assocClassName, resultClassName, 
                        role, resultRole):
            yield i 
        logger.log_debug('CIMProvider MI_associatorNames returning')

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
        logger.log_debug('CIMProvider MI_references called. resultClass: %s' % (resultClassName))
        cname = resultClassName
        if not cname:
            return
        for i in self._get_callable(cname, 'MI_references')  \
                           (env, 
                            objectName, 
                            resultClassName, 
                            role, 
                            propertyList):
            yield i 
        logger.log_debug('CIMProvider MI_references returning')

##############################################################################
# referenceNames
##############################################################################
    def MI_referenceNames(self, 
                          env, 
                          objectName, 
                          resultClassName, 
                          role):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_referenceNames <1> called. resultClass: %s' % (resultClassName))
        cname = resultClassName
        if not cname:
            return
        for i in self._get_callable(cname, 'MI_referenceNames')  \
               (env, 
                objectName, 
                resultClassName, 
                role):
            yield i 
        logger.log_debug('CIMProvider MI_referenceNames returning')

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
    def MI_invokeMethod(self, env, objectName, metaMethod, inputParams):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_invokeMethod called. method: %s:%s' \
                % (objectName.classname,metaMethod.name))
        rval = self._get_callable(objectName.classname, 'MI_invokeMethod')  \
                (env, objectName, metaMethod, inputParams)
        logger.log_debug('CIMProvider MI_invokeMethod returning')
        return rval
            
##############################################################################
    def MI_poll (self, env):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_poll called')
        if hasattr(self.provmod, 'poll'):
            rval = self.provmod.poll(env)
        elif hasattr(self.provmod, 'MI_poll'):
            rval = self.provmod.MI_poll(env)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                     "Provider %s has no support for polling"%self.provid)
        logger.log_debug('CIMProvider MI_poll returning %s' % str(rval))
        return rval

##############################################################################
    def MI_getInitialPollingInterval (self, env):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_poll called')
        if hasattr(self.provmod, 'get_initial_polling_interval'):
            rval = self.provmod.get_initial_polling_interval(env)
        elif hasattr(self.provmod, 'MI_getInitialPollingInterval'):
            rval = self.provmod.MI_getInitialPollingInterval(env)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                     "Provider %s has no support for polling"%self.provid)
        logger.log_debug('CIMProvider MI_poll returning %s' % str(rval))
        return rval

##############################################################################
    def MI_activateFilter (self, 
                           env, 
                           filter,
                           namespace,
                           classes,
                           firstActivation):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_activateFilter called')
        if hasattr(self.provmod, 'activate_filter'):
            self.provmod.activate_filter(env, filter, namespace,
                    classes, firstActivation)
        elif hasattr(self.provmod, 'MI_activateFilter'):
            self.provmod.MI_activateFilter(env, filter, namespace,
                    classes, firstActivation)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Provider %s has no support for activate filter"%self.provid)
        logger.log_debug('CIMProvider MI_activateFilter returning')

                    
##############################################################################
    def MI_deActivateFilter(self,
                            env,
                            filter,
                            namespace,
                            classes,
                            lastActivation):
        logger = env.get_logger()
        logger.log_debug('CIMProvider MI_deActivateFilter called')
        if hasattr(self.provmod, 'deactivate_filter'):
            self.provmod.deactivate_filter(env, filter, namespace, classes,
                    lastActivation)
        elif hasattr(self.provmod, 'MI_deActivateFilter'):
            self.provmod.MI_deActivateFilter(env, filter, namespace, classes,
                    lastActivation)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Provider %s has no support for deactivate filter"%self.provid)
        logger.log_debug('CIMProvider MI_deActivateFilter returning')


##############################################################################
    def MI_shutdown (self, env):
        modname = self.provmod.__name__
        if hasattr(self.provmod, "shutdown"):
            self.provmod.shutdown(env)
        self.provmod = None
        del sys.modules[modname]
        #TODO concurrency problems here??


##############################################################################
    def MI_canunload(self, env):
        if hasattr(self.provmod, "canunload"):
            return self.provmod.canunload
        else:
            return True

##############################################################################
    def MI_consumeIndication(self,
                            env,
                            destinationPath,
                            indicationInstance):

        logger = env.get_logger()
        logger.log_debug('ProviderProxy MI_consumeIndication called')
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
 
