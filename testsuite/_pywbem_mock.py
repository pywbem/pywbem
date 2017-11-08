#!/usr/bin/env python

# (C) Copyright 2017 IBM Corp.
# (C) Copyright 2017 Inova Development Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Prototype test of using mock to enable tests of pywbemcli with pytest as
the test driver.

Creates a class for each pywbemcli subcommand.
"""
from __future__ import absolute_import, print_function

from pprint import pprint as pp  # noqa: F401
from mock import Mock
import six

from pywbem import WBEMConnection, CIMClass, CIMInstance, \
    CIMQualifierDeclaration, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_FAILED, CIM_ERR_INVALID_SUPERCLASS, \
    CIM_ERR_INVALID_CLASS, CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_NAMESPACE, \
    DEFAULT_NAMESPACE
from pywbem.cim_obj import NocaseDict

#
#   Prototype mocking
#

__all__ = ['FakedWBEMConnection']


class FakedWBEMConnection(WBEMConnection):
    """
    A faked WBEMConnection class that mocks _imethodcall and _methodcall
    WBEMConnection methods and creates equivalents for all of
    the WBEMConnection methods that communicate with the server.
    Because it only mocks _imethodcall and _methodcall all of the logic in
    the various WBEMConneciton methods that prepare requests for the server
    (ex. GetClass) is utilized and the parameters of the method calls are
    tested/modified, etc.
    """
    def __init__(self, verbose=None):
        super(FakedWBEMConnection, self).__init__(
            'http://FakedUrl', default_namespace=DEFAULT_NAMESPACE,
            # creds=None,
            # x509=None, verify_callback=None, ca_certs=None,
            # no_verifi cation=False, timeout=None,
            use_pull_operations=False,
            enable_stats=False)

        # Dictionary of classes representing a repository.  This is
        # a dictionary of dictionaries where the top level key is
        # namespace and the keys for each dictionary in a namespace are
        # class names in the repository. The values in each subdirectory are
        # CIMClass objects.
        self.classes = {}

        # Same format as classes above, dictionary of dictionaries where
        # the top level keys are namespaces and the next level kesy are
        # CIMQualifierDeclaration names with values of the
        # CIMQualifierDeclaration objects
        self.qualifiers = {}

        # Top level dictionary: key is namespace, value is dictionary
        # and value is list of instances
        self.instances = {}

        self.verbose = verbose

        self._imethodcall = Mock(side_effect=self.mock_imethodcall)

    ##########################################################
    #
    #   Functions Mocked
    #
    ##########################################################

    def mock_imethodcall(self, methodname, namespace, response_params_rqd=None,
                         **params):
        """
        Mock the WBEMConnection _imethod call.

        This mock calls functions within this class that fake the processing
        in a WBEM server (at the CIM Object level) for the varisous CIM/XML
        methods and return.

        Each function is named with the lower case method namd prepended with
        'fake_'.
        """
        if self.verbose:
            print('mock_imethodcall method=%s, ns=%s, rsp_params=%s\nparams=%s'
                  % (methodname, namespace, response_params_rqd, params))

        method_name = 'fake_' + methodname.lower()

        method_name = getattr(self, method_name)
        result = method_name(namespace, params)
        if self.verbose:
            print('mock result %s' % result)
        return result

    def mock_methodcall(self, methodname, localobject, Params=None, **params):
        """
        """
        pass

    ################################################################
    #
    #   Methods to insert data into fake repository
    #
    ################################################################

    def display_repository(self):
        """
        Display everything in repository
        """
        def display_objects(self, obj_type, objects_dict):
            if not objects_dict:
                return
            for ns, objects in six.iteritems(objects_dict):
                print('namespace %s: %s classes' % (ns, obj_type,
                                                    len(objects)))
                for name, object in six.iteritems(objects):
                    print(object.tomof())

        self.display_objects('classes', self.classes)

        self.display_objects('instances', self.classes)

        self.display_objects('instances', self.classes)

    def add_cimobjects(self, objects, namespace=DEFAULT_NAMESPACE):
        """
            Add  a CIM object (CIMClass, CIMInstance, CIMQualifierDecl)
            or list of objects to the faked repository.

            This allows the user to create objects directly and insert them
            into the repository for tests.
        """
        if isinstance(objects, list):
            for object in objects:
                self.add_cimobjects(object)

            if self.verbose:
                if self.classes:
                    # pp(self.classes)
                    for ns in self.classes:
                        classes = self.classes[ns]
                        print('namespace %s qual count %s' % (ns, len(classes)))
                        for cname in classes:
                            cl = classes[cname]
                            print(cl.tomof())
                if self.qualifiers:
                    for ns in self.qualifiers:
                        quals = self.qualifiers[ns]
                        print('namespace %s qual count %s\n' % (ns, len(quals)))
                        for qname in quals:
                            q = quals[qname]
                            print(q.tomof())
                    # pp(self.qualifiers)

        else:
            obj = objects
            if isinstance(obj, CIMClass):
                cc = obj
                if cc.superclass:
                    try:
                        _ = self.GetClass(cc.superclass,  # noqa: F841
                                          LocalOnly=True,
                                          IncludeQualifiers=False)
                    except CIMError as ce:
                        if ce.args[0] == CIM_ERR_NOT_FOUND:
                            ce.args = (CIM_ERR_INVALID_SUPERCLASS,
                                       cc.superclass)
                            raise
                        else:
                            raise
                try:
                    # The following generates an exception for each new ns
                    self.classes[namespace][cc.classname] = cc
                except KeyError:
                    self.classes[namespace] = NocaseDict({cc.classname: cc})

            elif isinstance(obj, CIMInstance):
                inst = obj
                try:
                    self.instances[namespace].append(inst)
                except KeyError:
                    self.instances[namespace] = [inst]

            elif isinstance(obj, CIMQualifierDeclaration):
                qual = obj
                try:
                    self.qualifiers[namespace][qual.name] = qual
                except KeyError:
                    self.qualifiers[namespace] = NocaseDict({qual.name: qual})

            else:
                raise ValueError('add_cimobjects. %s not valid' % obj)

    def class_exists(self, namespace, cl):
        """
        Test if class exists in repository namespace
        """
        if namespace in self.classes:
            if self.classes[namespace][cl]:
                return True
        return False

    @staticmethod
    def make_tuple(rtn_value):
        """
        Make the return value into a tuple in accord with _imethodcall
        """
        return [("IRETURNVALUE", {}, rtn_value)]

    #####################################################################
    #
    #          Faked WBEMConnection Class methods
    #
    ######################################################################

    def get_subclasses(self, class_name):
        """
            Get classes that are immediate subvclasses of the
            class defined on input. That is all classes in the table
            for which this class is the superclass.
        """
        # cls = [cl in self.classes if cl.superclass == class_name]
        cls = []
        for cl in self.classes:
            if cl.superclass == class_name:
                cls.append(cl)
        return cls

    def fake_enumerateclasses(self, namespace, *args, **kwargs):
        """
        Enumerate classes from class dictionary. If classname parameter
        exists, use it as the starting poing
        """
        if 'classname' in kwargs:
            start_cn = kwargs['classname']
        else:
            start_cn = None

        classes = self.get_subclasses(start_cn)

        if kwargs['DeepInheritance']:
            pass
            # TODO recursively do the rest

        raise CIMError(CIM_ERR_FAILED, 'Not implemented!')

    def fake_getclass(self, namespace, *args, **kwargs):
        """Retrieve a CIM class from the local repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """
        print('mock_GetClass args %s kwargs %s' % (args, kwargs))

        cname = args[0]['ClassName'] if args else kwargs['ClassName']
        cname = cname.classname

        try:
            cc = self.classes[namespace][cname]
        except KeyError as ke:
            print('keyerror %s' % ke)
            ce = CIMError(CIM_ERR_NOT_FOUND, 'class %s not found' % cname)
            raise ce
        if 'LocalOnly' in kwargs and not kwargs['LocalOnly']:
            if cc.superclass:
                try:
                    del kwargs['ClassName']
                except KeyError:
                    pass
                if args:
                    args = args[1:]
                super_ = self.GetClass(cc.superclass, *args, **kwargs)
                for prop in super_.properties.values():
                    if prop.name not in cc.properties:
                        cc.properties[prop.name] = prop
                for meth in super_.methods.values():
                    if meth.name not in cc.methods:
                        cc.methods[meth.name] = meth

        # return the class
        return self.make_tuple(cc)

    ##########################################################
    #
    #              Faked Qualifier methods
    #
    ###########################################################

    def fake_enumeratequalifiers(self, namespace, *args, **kwargs):
        """Enumerate the qualifier types in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        try:
            qualifiers = list(self.qualifiers[namespace].values())
        except KeyError:
            pass
        return self.make_tuple(qualifiers)

    def fake_getqualifier(self, namespace, *args, **kwargs):
        """Retrieve a qualifier type from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """
        qname = args[0] if args else kwargs['QualifierName']
        qname = qname['QualifierName']
        # TODO why above the args return a single item dictionary???
        print('fake_get_qualifier ns %s name %s' % (namespace, qname))
        try:
            qualifier = self.qualifiers[namespace][qname]
            print('qual=%s' % qualifier)
            return self.make_tuple([qualifier])
        except KeyError:
            ce = CIMError(CIM_ERR_NOT_FOUND, qname)
            raise ce

    def fake_setqualifier(self, namespace, *args, **kwargs):
        """Create or modify a qualifier type in the local repository of this
        class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """
        qname = args[0] if args else kwargs['QualifierDeclaration']
        qname = qname['QualifierName']
        qualifier = None

        if qname in self.qualifiers[namespace]:
            raise CIMError(CIM_ERR_ALREADY_EXISTS, '%s' % qname)
        try:
            self.qualifiers[namespace] = NocaseDict({qualifier.name: qualifier})
        except KeyError as ke:
            print('setqualifier key error %s' % ke)
            # TODO sort out what to do here.

    def fake_deletequalifier(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        qname = args[0] if args else kwargs['QualifierDeclaration']
        qname = qname['QualifierName']

        if qname in self.qualifiers[namespace]:
            del self.qualifiers[qname]
        else:
            raise CIMError(CIM_ERR_NOT_FOUND, 'qualifier decl %s not found'
                           % qname)

    #####################################################################
    #
    #  Faked WBEMConnection Instance methods
    #
    #####################################################################

    def fake_createinstance(self, namespace, *args, **kwargs):
        """Create a CIM instance in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """

        new_inst = args[0] if args else kwargs['NewInstance']

        if self.class_exists(namespace, new_inst.classname):
            # TODO add host and correct namespace to newinst path
            try:
                for inst in self.instances[namespace]:
                    if inst.path == new_inst.path:
                        raise CIMError(CIM_ERR_ALREADY_EXISTS,
                                       'Instance %s exists in namespace %s' %
                                       (new_inst.path, namespace))
                self.instances[namespace].append(new_inst)
            except KeyError:
                self.instances[namespace] = [new_inst]
            return new_inst.path
        else:
            raise CIMError(CIM_ERR_INVALID_CLASS, 'class %s does not exist' %
                           inst.classname)

    def fake_getinstance(self, namespace, *args, **kwargs):
        """
        Executes the equilavent of the WBEMConnection GetInstance
        for an instance in the instances dictionary
        """
        print('ns %s\nargs=%s\nkwargs=%s' % (namespace, args, kwargs))
        iname = args[0]['InstanceName'] if args else kwargs['InstanceName']
        # iname = iname.instancename
        cname = iname.classname
        # iname_str = '%s' % iname

        try:
            print('getting ns %s class %s' % (namespace, cname))
            insts = self.instances[namespace]
        except KeyError as ke:
            print('keyerror %s' % ke)
            ce = CIMError(CIM_ERR_NOT_FOUND, iname)
            raise ce
        for inst in insts:
            if iname == inst.path:
                # TODO filter properties, etc. from instance
                return self.make_tuple(inst)

            ce = CIMError(CIM_ERR_NOT_FOUND, iname)
            raise ce

    def fake_enumerateinstances(self, namespace, *args, **kwargs):
        """
        Executes the equilavent of the WBEMConnection GetInstance
        for an instance in the instances dictionary
        """
        cname = args[0]['ClassName'] if args else kwargs['ClassName']

        insts = []
        try:
            print('getting ns %s instances %s' % (namespace, cname))
            insts = self.Instances[namespace]
        except KeyError as ke:
            print('keyerror %s' % ke)
            raise CIMError(CIM_ERR_INVALID_NAMESPACE, '%s' % namespace)

        # filter instances to this class and subclasses

        insts = [inst for inst in insts if inst.path.classname == cname]

        # TODO filter properties, etc. from instance
        # ClassName, namespace=None, LocalOnly=None,
        #                   DeepInheritance=None, IncludeQualifiers=None,
        #                   IncludeClassOrigin=None, PropertyList=None
        return self.make_tuple(insts)

    def fake_execquery(self, namespace, *args, **kwargs):
        """
        Executes the equilavent of the WBEMConnection ExecQuery for
        the querylanguage and query defined
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def filter_instance(self, instance, LocalOnly, DeepInheritance,
                        IncludeQualifiers, IncludeClassOrigin, PropertyList):
        """
        Clean a single instance based on the input parameters. Note that we
        can only filter if the class is in the class repository.
        """
        return instance

    #####################################################################
    #
    #  Faked WBEMConnection Reference and Associator methods
    #
    #####################################################################

    def fake_references(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_referencenames(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_associators(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_associatorNames(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    #####################################################################
    #
    #  Faked WBEMConnection Open and Pull Instances Methods
    #
    #####################################################################

    def fake_openenumerateinstancepaths(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_openenumerateinstances(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_openreferenceinstancepaths(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_openreferenceinstances(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_openassociatorinstancepaths(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_openassociatorinstances(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_openqueryInstances(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_pull_instanceswithpath(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_pull_instances(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    def fake_closeenumeration(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    #####################################################################
    #
    #  Faked WBEMConnection InvokeMethod
    #
    #####################################################################

    def fake_invokemethod(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """
        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')
