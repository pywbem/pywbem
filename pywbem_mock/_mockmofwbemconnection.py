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
    CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_SUPERCLASS
from pywbem._nocasedict import NocaseDict
from pywbem._mof_compiler import BaseRepositoryConnection
from pywbem._utils import _format
from ._resolvermixin import ResolverMixin


class _MockMOFWBEMConnection(BaseRepositoryConnection, ResolverMixin):
    """
    Create an adaption of the MOF compiler BaseRepositoryConnection class to
    interface through the client API to the FakedWBEMConnection acting as the
    interface to the CIM repository for mocking a WBEM server

    This class adaption is private to pywbem_mock
    """
    def __init__(self, faked_conn_object):
        """
        Initialize the connection.

          Parameters:

            faked_conn_object (:class:`~pywbem_mock.FakedWBEMConnection`):
              The object providing the CIM repository.
        """

        self.classes = NocaseDict()

        self.conn = faked_conn_object
        self.conn_id = self.conn.conn_id

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

    getns = _getns  # for compatibility, used in the MOF compiler

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
        """
        Not Implemented because not used with the MOF compiler.
        """

        assert False, 'EnumerateInstanceNames not implemented!'

    def CreateInstance(self, *args, **kwargs):
        """
        Create a CIM instance in the connected client.

        This method:

        1. Validates properties and the class
        2. Sets the instance path to None to assuming that the
           conn.CreateInstance creates a complete path.
        3. Passes the NewInstance to conn.CreateInstance (the client
           that is connected to a repository)

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """

        inst = args[0] if args else kwargs['NewInstance']

        ns = kwargs.get('namespace', self.default_namespace)

        # Get list of properties in class defined for this instance
        cln = inst.classname
        cls = self.GetClass(cln, namespace=ns, IncludeQualifiers=True,
                            LocalOnly=False)

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

        # Insure inst.path is empty before calling CreateInstance so that
        # the path is built by CreateInstance. This is logical because
        # the mock environment always requires a complete path to insert
        # an instance into the repository.
        inst.path = None

        try:
            path = self.conn.CreateInstance(inst, namespace=ns)
        except KeyError:  # pylint: disable=try-except-raise
            raise
        return path

    def ModifyInstance(self, *args, **kwargs):
        """
        This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to create an instance.

        NOTE: It does NOT support the propertylist attribute that is part
        of the CIM/XML definition of ModifyInstance and it requires that
        each created instance include the instance path which means that
        the MOF must include the instance alias on each created instance.
        """

        mod_inst = args[0] if args else kwargs['ModifiedInstance']

        self.conn.ModifyInstance(mod_inst.path)

    def DeleteInstance(self, *args, **kwargs):
        """
        Not implemented because not used by the MOF compiler
        """
        assert False, 'DeleteInstance not implemented!'

    def GetClass(self, *args, **kwargs):
        """Retrieve a CIM class from the local classes store if it exists
        there or from the client interface defined by self.conn.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """

        cname = args[0] if args else kwargs['ClassName']
        ns = kwargs.get('namespace', self.default_namespace)

        try:
            cc = self.classes[ns][cname]
        except KeyError:
            cc = self.conn.GetClass(*args, **kwargs)
            try:
                self.classes[ns][cc.classname] = cc
            except KeyError:
                self.classes[ns] = NocaseDict({cc.classname: cc})

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
        Override the CreateClass method in BaseRepositoryConnection.
        Implements creation of the class through the connected client and
        also sets it in the local client (NocaseDict).

        This Create class implementation is special for the MOF compiler
        because it includes the logic to retrieve classes missing from the
        repository but required to define a correct repository.  That includes
        superclasses and other classes referenced by the class being defined.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """
        cc = args[0] if args else kwargs['NewClass']
        ns = kwargs.get('namespace', self.default_namespace)

        if cc.superclass:
            # Since this may cause additional GetClass calls
            # IncludeQualifiers = True insures reference properties on
            # instances with aliases get built correctly.
            try:
                self.GetClass(cc.superclass, namespace=ns, LocalOnly=True,
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
            self.classes[ns][cc.classname] = cc
        except KeyError:
            self.classes[ns] = NocaseDict({cc.classname: cc})

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
                    self.GetClass(obj.reference_class, namespace=ns,
                                  LocalOnly=True, IncludeQualifiers=True)
                except KeyError:
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   obj.reference_class)
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
                    del self.classes[ns][cc.classname]
                    raise

            elif obj.type == 'string':
                if 'EmbeddedInstance' in obj.qualifiers:
                    eiqualifier = obj.qualifiers['EmbeddedInstance']
                    try:
                        self.GetClass(eiqualifier.value, namespace=ns,
                                      LocalOnly=True,
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
                        del self.classes[ns][cc.classname]
                        raise

        self.conn.CreateClass(cc, namespace=ns)

    def ModifyClass(self, *args, **kwargs):
        """
        This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to execute CreateClass.

        It executes a ModifyClass on the connected client

        """
        modified_class = args[0] if args else kwargs['ModifiedClass']
        ns = kwargs.get('namespace', self.default_namespace)

        self.conn.ModifyClass(modified_class, namespace=ns)

    def DeleteClass(self, *args, **kwargs):
        """
        Not implemented because not called from the MOF compiler
        """

        assert False, 'DeleteClass not implemented!'

    def EnumerateQualifiers(self, *args, **kwargs):
        """Enumerate the qualifier types throught the connected client.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        rv = self.conn.EnumerateQualifiers(*args, **kwargs)

        return rv

    def GetQualifier(self, *args, **kwargs):
        """Retrieve a qualifier type from the connected client.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """

        qualname = args[0] if args else kwargs['QualifierName']
        ns = kwargs.get('namespace', self.default_namespace)

        try:
            qual = self.conn.GetQualifier(qualname, namespace=ns)
        except KeyError:  # pylint: disable=try-except-raise
            raise
        return qual

    def SetQualifier(self, *args, **kwargs):
        """Create or modify a qualifier type in the connected client

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """
        qual = args[0] if args else kwargs['QualifierDeclaration']
        ns = kwargs.get('namespace', self.default_namespace)

        self.conn.SetQualifier(qual, namespace=ns)

    def DeleteQualifier(self, *args, **kwargs):
        """
        Not implemented because not called from the MOF compiler
        """

        assert False, 'DeleteQualifier not implemented!'
