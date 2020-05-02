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

# Issue #2062 TODO/ks Remove this code and use the methods in _WBEMConnection
# in their place


class _MockMOFWBEMConnection(MOFWBEMConnection, ResolverMixin):
    """
    Create an adaption of the MOF compiler MOFWBEMConnection class to interface
    through the client API to the FakedWBEMConnection acting as the
    interface to the CIM repository

    This class adaption is private to pywbem_mock
    """
    def __init__(self, faked_conn_object):
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

        self.conn = faked_conn_object
        self.conn_id = self.conn_id

    def _getns(self):
        """
        :term:`string`: Return the default repository namespace to be used.

        This method exists for compatibility. Use the :attr:`default_namespace`
        property instead.
        """
        return self.conn.default_namespace

    def _setns(self, value):
        """
        Set the default repository namespace to be used.

        This method exists for compatibility. Use the :attr:`default_namespace`
        property instead.
        """
        self.conn.default_namespace = value

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

        inst = args[0] if args else kwargs['NewInstance']

        # Get list of properties in class defined for this instance
        # TODO should this get from conn
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

	# insure inst.path is empty before calling CreateInstance so that
        # the path is built by CreateInstance. This is logical because
        # the mock environment always requires a complete path to insert
        # an instance into the repository.
	inst.path = None
        try:
            self.conn.CreateInstance(inst)
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
        # namespace = self.default_namespace
        mod_inst = args[0] if args else kwargs['ModifiedInstance']
        # # pylint: disable=protected-access
        # instance_store = self.conn._get_instance_store(namespace)

        # if self.default_namespace not in self.repo.namespaces:
            # raise CIMError(
                # CIM_ERR_INVALID_NAMESPACE,
                # _format('ModifyInstance failed. No instance repo exists. '
                        # 'Use compiler instance alias to set path on '
                        # 'instance declaration. inst: {0!A}', mod_inst))

        # if not instance_store.object_exists(mod_inst.path):
            # raise CIMError(
                # CIM_ERR_NOT_FOUND,
                # _format('ModifyInstance failed. No instance exists. '
                        # 'Use compiler instance alias to set path on '
                        # 'instance declaration. inst: {0!A}', mod_inst))

        # Update the instance in the repository from the modified inst
        #orig_inst = instance_store.get(mod_inst.path)
        #orig_inst.update(mod_inst.properties)
        #instance_store.update(mod_inst.path, orig_inst)
        # TODO: Do I have to do the update or does ModifyInstance
        #orig_inst = self.conn.GetInstance(mod_inst.path)
        #orig_inst.update(mod_inst.properties)
        self.conn.ModifyInstance(mod_inst.path)

    def DeleteInstance(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def GetClass(self, *args, **kwargs):
        """Retrieve a CIM class from the local classes store if it exists
        there or from the cim repository reached through conn.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """

        cname = args[0] if args else kwargs['ClassName']

        try:
            cc = self.classes[self.default_namespace][cname]
        except KeyError:
            cc = self.conn.GetClass(*args, **kwargs)
            try:
                self.classes[self.default_namespace][cc.classname] = cc
            except KeyError:
                self.classes[self.default_namespace] = \
                    NocaseDict({cc.classname: cc})

        # TODO: Do we even need this except for when we get class from
        # the local store?
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
        # the test code below without previously putting the class into
        # the repository defined by conn.
        try:
            # The following generates an exception for each new ns
            self.classes[self.default_namespace][cc.classname] = cc
        except KeyError:
            self.classes[self.default_namespace] = NocaseDict({cc.classname: cc})

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
                    # NOTE: Only delete when this is total failure
                    del self.classes[self.conn.default_namespace][cc.classname]
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
                        # Only delete when total failure
                        del self.classes[self.default_namespace][cc.classname]
                        raise

        self.conn.CreateClass(cc)

    def EnumerateQualifiers(self, *args, **kwargs):
        """Enumerate the qualifier types in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        rv = self.conn.EnumerateQualifiers(*args, **kwargs)
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
        try:
            qual = self.conn.GetQualifier(qualname)
        except KeyError:
            raise
        return qual

    def SetQualifier(self, *args, **kwargs):
        """Create or modify a qualifier type in the local repository of this
        class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """
        #namespace = self.default_namespace
        qual = args[0] if args else kwargs['QualifierDeclaration']
        #qualifier_store = self.repo.get_qualifier_store(namespace)
        self.conn.SetQualifier(qual)

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
        # TODO: Should we delete this???
        return self.GetClass(superclass,
                             namespace=namespace,
                             local_only=local_only,
                             include_qualifiers=include_qualifiers,
                             include_classorigin=include_classorigin)
