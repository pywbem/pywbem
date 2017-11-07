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

import unittest
from mock import Mock

from pywbem import WBEMConnection, CIMClass, CIMProperty, CIMInstance, \
    CIMInstanceName, CIMQualifier, CIMQualifierDeclaration, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_FAILED, CIM_ERR_INVALID_SUPERCLASS, \
    DEFAULT_NAMESPACE
from pywbem.cim_obj import NocaseDict

#
#   Prototype mocking
#


class FakedWBEMConnection(WBEMConnection):
    """
    A faked WBEMConnection class that mocks _imethodcall and method call
    and creates equivalents for all of the WBEMConnection methods that
    communicate with the server.
    It retains all of the methods from WBEConnection and simply mocks the
    common call to _methodclall and _imethodcall
    """
    def __init__(self):
        super(FakedWBEMConnection, self).__init__(
            'http://FakedUrl', default_namespace=DEFAULT_NAMESPACE,
            # creds=None,
            # x509=None, verify_callback=None, ca_certs=None,
            # no_verifi cation=False, timeout=None,
            use_pull_operations=False,
            enable_stats=False)
        # self.url = 'http://FakedUrl'
        print('url %s host %s' % (self.url, self.host))
        # these dictionaries are all the same form:
        # key is classname, value is dictionary of elements with key being
        # the element name (classname, qualifierdecl name, instance name)
        self.class_names = {}
        self.qualifiers = {}
        self.instances = {}
        self.classes = {}
        self._imethodcall = Mock(side_effect=self.mock_imethodcall)

    def mock_imethodcall(self, methodname, namespace, response_params_rqd=None,
                         **params):
        """
        """
        print('mock_imethodcall method=%s, ns=%s, rsp_params=%s\nparams=%s' %
              (methodname, namespace, response_params_rqd, params))

        method_name = 'fake_' + methodname.lower()

        print('Calling %s\nparams:%s' % (method_name, params))
        method_name = getattr(self, method_name)
        result = method_name(namespace, params)
        print('mock result %s' % result)
        return result

    def mock_methodcall(self, methodname, localobject, Params=None, **params):
        """
        """
        pass

    def add_objects(self, objects, namespace=DEFAULT_NAMESPACE)
        """
            Add a CIM object (CIMClass, CIMInstance, CIMQualifierDecl)
            or list of objects to the faked repository
        """
        if isinstance(classes, list):
            for class_ in classes:
                self.add_classes(class_)
        else:
            obj = objects
            if isinstance(CIMClass, obj):

            elif isinstance(CIMInstance, obj):
                inst = obj
                classname = inst.classname
                try:
                    self.instances[namespace][classname].append(inst)
                except KeyError:
                    self.instances[namespace] = {}
                    self.instances[namespace][classname] = [inst]

            elif isinstance(CIMQualifierDecl, obj):
                qual_decl = obj
                self.mock_createqualifier(qual_decl, namespace=namespace)


    def add_classes(self, classes, namespace=DEFAULT_NAMESPACE):
        """
        Add the defined class to the class repository that will be used in
        the test.

          Parameters:
             Classes: List of CIMClasses or CIMClass
        """
        if isinstance(classes, list):
            for class_ in classes:
                self.add_classes(class_)
        else:
            cc = classes
            if cc.superclass:
                try:
                    _ = self.GetClass(cc.superclass,  # noqa: F841
                                      LocalOnly=True, IncludeQualifiers=False)
                except CIMError as ce:
                    if ce.args[0] == CIM_ERR_NOT_FOUND:
                        ce.args = (CIM_ERR_INVALID_SUPERCLASS,
                                   cc.superclass)
                        raise
                    else:
                        raise
            ns = namespace if namespace else self.default_namespace
            try:
                # The following generates an exception for each new ns
                self.classes[ns][cc.classname] = cc
            except KeyError:
                self.classes[ns] = \
                    NocaseDict({cc.classname: cc})

    def add_instances(self, instances, namespace=DEFAULT_NAMESPACE):
        """
        Add the defined class to the class repository that will be used in
        the test.

          Parameters:
             Classes: List of CIMInstances with path component.
        """
        print('add_instances ns %s' % namespace)
        if isinstance(instances, list):
            for instance in instances:
                self.add_instances(instance)
        else:
            inst = instances
            classname = inst.classname
            try:
                self.instances[namespace][classname].append(inst)
            except KeyError:
                self.instances[namespace] = {}
                self.instances[namespace][classname] = [inst]

    @staticmethod
    def make_tuple(rtn_value):
        """
        Make the return value into a tuple in accord with _imethodcall
        """
        return [("IRETURNVALUE", {}, [rtn_value])]

    # ###################### Class methods

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
            print('getting ns %s class %s' % (namespace, cname))
            cc = self.classes[namespace][cname]
        except KeyError as ke:
            print('keyerror %s' % ke)
            ce = CIMError(CIM_ERR_NOT_FOUND, cname)
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

        return self.make_tuple(cc)

    # ##################Qualifier methods

    def fake_enumeratequalifiers(self, namespace, *args, **kwargs):
        """Enumerate the qualifier types in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        try:
            rv = list(self.qualifiers[namespace].values())
        except KeyError:
            pass
        return rv

    def fake_getqualifier(self, namespace, *args, **kwargs):
        """Retrieve a qualifier type from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """

        qualname = args[0] if args else kwargs['QualifierName']
        try:
            qual = self.qualifiers[namespace][qualname]
            return qual
        except KeyError:
            ce = CIMError(CIM_ERR_NOT_FOUND, qualname)
            raise ce

    def fake_setqualifier(self, namespace, *args, **kwargs):
        """Create or modify a qualifier type in the local repository of this
        class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """

        qual = args[0] if args else kwargs['QualifierDeclaration']

        try:
            self.qualifiers[namespace][qual.name] = qual
        except KeyError:
            self.qualifiers[namespace] = NocaseDict({qual.name: qual})

    def fake_deletequalifier(self, namespace, *args, **kwargs):
        """
            This method deletes a single qualifier if it is in the
            repository for this class and namespace
        """

        raise CIMError(CIM_ERR_FAILED, 'Not Implemented!')

    # ###############Instance methods

    def fake_createinstance(self, namespace, *args, **kwargs):
        """Create a CIM instance in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """

        inst = args[0] if args else kwargs['NewInstance']
        classname = inst.classname
        # TODO test to assure inst not already in list.
        try:
            self.instances[namespace][classname].append(inst)
        except KeyError:
            self.instances[namespace][classname] = [inst]
        return inst.path

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
            insts = self.instances[namespace][cname]
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
            insts = self.Instances[namespace][cname]
        except KeyError as ke:
            print('keyerror %s' % ke)

        # TODO filter properties, etc. from instance
        #ClassName, namespace=None, LocalOnly=None,
        #                   DeepInheritance=None, IncludeQualifiers=None,
        #                   IncludeClassOrigin=None, PropertyList=None
        return self.make_tuple(insts)

    def clean_instance(self,instance, LocalOnly, DeepInheritance,
                       IncludeQualifiers,
                       IncludeClassOrigin, PropertyList):
        """
        Clean a single instance based on the input parameters
        """
        return instance


class ClassOperationMockTests(object):
    """
    Test mocking of Class level operations
    """

    def get_class(self):
        """
        Test mocking wbemconnection getClass accessed through pywbemtools
        class get

        test using Mock directly and returning a class.

        Currently fails  result <Result SystemExit(1,)>
        """
        conn = FakedWBEMConnection()

        c = CIMClass(
            'CIM_Foo', properties={'InstanceID':
                                   CIMProperty('InstanceID', None,
                                               type='string')})
        print('created class %r' % c)

        conn.add_classes(c)
        cl = conn.GetClass('CIM_Foo')
        print('getclass returns %s' % cl.tomof())


class InstanceOperationMockTests(object):

    def test_mock_get_instance(self):
        """
        Test mocking wbemconnection getClass accessed through pywbemtools
        class get

        test using Mock directly and returning a class.

        Currently fails  result <Result SystemExit(1,)>
        """
        fake_conn = FakedWBEMConnection()

        inst_path = CIMInstanceName('CIM_Foo', {'Name': 'Foo'})
        i = CIMInstance('CIM_Foo',
                        properties={'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers={'Key': CIMQualifier('Key', True)},
                        path=inst_path)
        print('created instance %r' % i)

        fake_conn.add_objects(i, namespace='root/cimv2')
        print('instances in rep %s' % fake_conn.instances)

        inst = fake_conn.GetInstance(inst_path)
        print('getinstance returns %s' % inst.tomof())
        inst_path.namespace = inst.path.namespace
        assertEqual(inst.path == inst_path)

