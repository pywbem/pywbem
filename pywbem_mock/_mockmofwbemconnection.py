#
# (C) Copyright 2018 InovaDevelopment.comn
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
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
Mock support for the WBEMConnection class to allow pywbem users to test the
pywbem client without requiring a running WBEM server.

For documentation, see mocksupport.rst.
"""

from __future__ import absolute_import, print_function

from pywbem import CIMError, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_NOT_FOUND, CIM_ERR_ALREADY_EXISTS, CIM_ERR_FAILED, \
    CIM_ERR_INVALID_SUPERCLASS, CIM_ERR_INVALID_NAMESPACE, CIMInstanceName
from pywbem._nocasedict import NocaseDict
from pywbem._mof_compiler import MOFWBEMConnection

from pywbem._utils import _format
from ._resolvermixin import ResolverMixin
from pywbem._nocasedict import NocaseDict

# Issue #2062 TODO/ks Remove this code and use the methods in _WBEMConnection
# in their place


class _MockMOFWBEMConnection(MOFWBEMConnection, ResolverMixin):
    """
    Create an adaption of the MOF compiler MOFWBEMConnection class so that to
    directly use the attributes that represent the repository and implement a
    modified CreateClass that resolves the new class. This directs the compiler
    output directly  to the dictionaries for qualifiers, and instances in the
    FakedWBEMConnection object and replaces the CreateClass with a local method
    that allows resolving the created class before it is inserted into the
    repository.

    This class adaption is private to pywbem_mock
    """
    def __init__(self, faked_conn_object, cimrepository):
        """
        Initialize the connection.

          Parameters:

            faked_conn_object (FakedWBEMConnection):
              The instance of _FakeWBEMConnection to which this is attached.
              This allows us to use the same objects for qualifiers, instances
              and classes as that object
        """
        super(_MockMOFWBEMConnection, self).__init__(conn=faked_conn_object)

        self.classes = NocaseDict()

        self.repo = cimrepository

    def _getns(self):
        """
        :term:`string`: Return the default repository namespace to be used.

        This method exists for compatibility. Use the :attr:`default_namespace`
        property instead.
        """
        if self.conn is not None:
            return self.conn.default_namespace
        return self.__default_namespace

    def _setns(self, value):
        """
        Set the default repository namespace to be used.

        This method exists for compatibility. Use the :attr:`default_namespace`
        property instead.
        """
        if self.conn is not None:
            self.conn.default_namespace = value
        else:
            self.__default_namespace = value

    getns = _getns  # for compatibility
    setns = _setns  # for compatibility

    default_namespace = property(
        _getns, _setns, None,
        """
        :term:`string`: The default repository namespace to be used.

        The default repository namespace is the default namespace of the
        underlying repository connection if there is such an underlying
        connection, or the default namespace of this object.

        Initially, the default namespace of this object is 'root/cimv2'.

        This property is settable. Setting it will cause the default namespace
        of the underlying repository connection to be updated if there is such
        an underlying connection, or the default namespace of this object.
        """
    )

    def EnumerateInstanceNames(self, *args, **kwargs):
        """This method is used by the MOF compiler only when it creates a
        namespace in the course of handling CIM_ERR_NAMESPACE_NOT_FOUND.
        Because the operations of this class silently create every namespace
        that is needed and never return that error, this method is never
        called, and is therefore not implemented.
        """

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def CreateInstance(self, *args, **kwargs):
        """
        Create a CIM instance in the local repository of this class.
        This method is derived from the the same method in the pywbem
        mof compiler but modified to:
        1. Use a dictionary as the container for instances where the
           key is the path. This means that all instances must have a
           path component to be inserted into the repository. Normally
           the path component is built within the compiler by using the
           instance alias.
        2. Fail with a CIMError exception if the instance already exists
           in the repository.


        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """
        namespace = self.default_namespace
        inst = args[0] if args else kwargs['NewInstance']

        # Get list of properties in class defined for this instance
        cln = inst.classname
        cls = self.GetClass(cln, IncludeQualifiers=True, LocalOnly=False)

        cls_key_properties = [p for p, v in cls.properties.items()
                              if 'key' in v.qualifiers]

        # Validate all key properties are in instance
        for pname in cls_key_properties:
            if pname not in inst.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format('CreateInstance failed. Key property {0!A}  in '
                            'class {1!A} but not in new_instance: {2!A}',
                            pname, cln, str(inst)))

        # Build path from instance and class
        if inst.path is None or not inst.path.keybindings:
            inst.path = CIMInstanceName.from_instance(
                cls, inst, namespace=self.default_namespace)

        # Exception if duplicate. NOTE: compiler overrides this with
        # modify instance.
        instance_store = self.repo.get_instance_store(namespace)
        if instance_store.exists(inst.path):
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format('CreateInstance failed. Instance with path {0!A} '
                        'already exists in mock repository', inst.path))
        try:
            # TODO: This should go through self.conn.CreateInstance
            instance_store.create(inst.path, inst)
        except KeyError:
            raise

        return inst.path

    def ModifyInstance(self, *args, **kwargs):
        """This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to create an instance.

        NOTE: It does NOT support the propertylist attribute that is part
        of the CIM/XML defintion of ModifyInstance and it requires that
        each created instance include the instance path which means that
        the MOF must include the instance alias on each created instance.
        """
        namespace = self.default_namespace
        mod_inst = args[0] if args else kwargs['ModifiedInstance']
        instance_store = self.conn._get_instance_store(namespace)

        if self.default_namespace not in self.repo.namespaces:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format('ModifyInstance failed. No instance repo exists. '
                        'Use compiler instance alias to set path on '
                        'instance declaration. inst: {0!A}', mod_inst))

        if not instance_store.exists(mod_inst.path):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format('ModifyInstance failed. No instance exists. '
                        'Use compiler instance alias to set path on '
                        'instance declaration. inst: {0!A}', mod_inst))

        # Update the instance in the repository from the modified inst
        orig_inst = instance_store.get(mod_inst.path)
        orig_inst.update(mod_inst.properties)
        instance_store.update(mod_inst.path, orig_inst)

    def DeleteInstance(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def GetClass(self, *args, **kwargs):
        """Retrieve a CIM class from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """
        cname = args[0] if args else kwargs['ClassName']

        try:
            cc = self.classes[self.default_namespace][cname]
        except KeyError:
            if self.conn is None:
                ce = CIMError(CIM_ERR_NOT_FOUND, cname)
                raise ce
            cc = self.conn.GetClass(*args, **kwargs)
            try:
                self.classes[self.default_namespace][cc.classname] = cc
            except KeyError:
                self.classes[self.default_namespace] = \
                    NocaseDict({cc.classname: cc})

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
        return cc

    def CreateClass(self, *args, **kwargs):
        """
        Override the CreateClass method in MOFWBEMConnection. NOTE: This is
        currently only used by the compiler.  The methods of Fake_WBEMConnectin
        go directly to the repository, not through this method.
        This modifies the overridden method to add validation.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """
        cc = args[0] if args else kwargs['NewClass']
        namespace = self.default_namespace
        class_store = self.repo.get_class_store(namespace)

        if cc.superclass:
            # Since this may cause additional GetClass calls
            # IncludeQualifiers = True insures reference properties on
            # instances with aliases get built correctly.
            try:
                self.GetClass(cc.superclass, LocalOnly=True,
                              IncludeQualifiers=True)
            except CIMError as ce:
                if ce.status_code == CIM_ERR_NOT_FOUND:
                    raise CIMError(
                        CIM_ERR_INVALID_SUPERCLASS,
                        _format("Cannot create class {0!A} in namespace "
                                "{1!A} because its superclass {2!A} does "
                                "not exist",
                                cc.classname, self.getns(), cc.superclass),
                        conn_id=self.conn_id)
                raise

        # Class created in local repo before tests because that allows
        # tests that may actually include this class to succeed in
        # the test code below.
        try:
            # The following generates an exception for each new ns
            self.classes[self.default_namespace][cc.classname] = cc
        except KeyError:
            self.classes[namespace] = NocaseDict({cc.classname: cc})

        # Validate that references and embedded instance properties, methods,
        # etc. have classes that exist in repo. This  also institates the
        # mechanism that gets insures that prerequisite classes are inserted
        # into the repo.
        objects = list(cc.properties.values())
        for meth in cc.methods.values():
            objects += list(meth.parameters.values())

        for obj in objects:
            # Validate that reference_class exists in repo
            if obj.type == 'reference':
                try:
                    self.GetClass(obj.reference_class, LocalOnly=True,
                                  IncludeQualifiers=True)
                except KeyError:
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   obj.reference_class)
                # TODO: When we hook to server this returns to CIMError
                except CIMError as ce:
                    if ce.status_code == CIM_ERR_NOT_FOUND:
                        raise CIMError(
                            CIM_ERR_INVALID_PARAMETER,
                            _format("Class {0!A} referenced by element {1!A} "
                                    "of class {2!A} in namespace {3!A} does "
                                    "not exist",
                                    obj.reference_class, obj.name,
                                    cc.classname, self.getns()),
                            conn_id=self.conn_id)
                    raise

            elif obj.type == 'string':
                if 'EmbeddedInstance' in obj.qualifiers:
                    eiqualifier = obj.qualifiers['EmbeddedInstance']
                    try:
                        self.GetClass(eiqualifier.value, LocalOnly=True,
                                      IncludeQualifiers=False)
                    except KeyError:
                        raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                       eiqualifier.value)
                    except CIMError as ce:
                        if ce.status_code == CIM_ERR_NOT_FOUND:
                            raise CIMError(
                                CIM_ERR_INVALID_PARAMETER,
                                _format("Class {0!A} specified by "
                                        "EmbeddInstance qualifier on element "
                                        "{1!A} of class {2!A} in namespace "
                                        "{3!A} does not exist",
                                        eiqualifier.value, obj.name,
                                        cc.classname, self.getns()),
                                conn_id=self.conn_id)
                        raise

        # TODO: Review this. Changed from conn to repo
        ccr = self.repo._resolve_class(  # pylint: disable=protected-access
            cc, namespace, self.repo.get_qualifier_store(namespace))

        # If the class exists, update it. Otherwise create it
        # TODO: Validate that this is correct behavior. That is what the
        # original MOFWBEMConnection does.
        if class_store.exists(ccr.classname):
            class_store.update(ccr.classname, ccr)
        else:
            class_store.create(ccr.classname, ccr)
        self.classes[namespace][ccr.classname] = ccr

    def EnumerateQualifiers(self, *args, **kwargs):
        """Enumerate the qualifier types in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        if self.conn is not None:
            rv = self.conn.EnumerateQualifiers(*args, **kwargs)
        else:
            rv = []
        try:
            rv += list(self.qualifiers[self.default_namespace].values())
        except KeyError:
            pass
        return rv

    def GetQualifier(self, *args, **kwargs):
        """Retrieve a qualifier type from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """

        qualname = args[0] if args else kwargs['QualifierName']
        namespace = self.default_namespace
        try:
            # TODO: This should get from real repo I think
            qualifier_store = self.repo.get_qualifier_store(namespace)
            qual = qualifier_store.get(qualname)
        except KeyError:
            raise
        return qual

    def SetQualifier(self, *args, **kwargs):
        """Create or modify a qualifier type in the local repository of this
        class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """
        namespace = self.default_namespace
        qual = args[0] if args else kwargs['QualifierDeclaration']
        qualifier_store = self.repo.get_qualifier_store(namespace)
        try:
            qualifier_store.create(qual.name, qual)
        except KeyError:
            # If qualifier already in repo, update it. This is defined
            # specification behavior
            qualifier_store.update(qual.name, qual)
            # raise
            # self.qualifiers[self.default_namespace] = \
            #    # NocaseDict({qual.name: qual})

    def DeleteQualifier(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def _get_class(self, superclass, namespace=None,
                   local_only=False, include_qualifiers=True,
                   include_classorigin=True):
        """
        This method is just rename of GetClass to support same method
        with both MOFWBEMConnection and FakedWBEMConnection
        """
        return self.GetClass(superclass,
                             namespace=namespace,
                             local_only=local_only,
                             include_qualifiers=include_qualifiers,
                             include_classorigin=include_classorigin)
