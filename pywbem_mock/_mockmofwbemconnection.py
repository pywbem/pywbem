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

from pywbem import MOFWBEMConnection, CIMError, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_NOT_FOUND
from pywbem._nocasedict import NocaseDict

from pywbem._utils import _format
from ._resolvermixin import ResolverMixin

# TODO: FutureUse the BaseWBEMConnection and recreate complete MOFWBEMConnection


class _MockMOFWBEMConnection(MOFWBEMConnection, ResolverMixin):
    """
    Create an adaption of the MOF compiler MOFWBEMConnection class so that to
    directly use the attributes that represent the repository and implement a
    modified CreateClass that resolves the new class. This directs the compiler
    output directly  to the dictionaries for qualifiers, and instances in the
    FakedWBEMConnection object and replaces the CreateClass with a local method
    that allows resolving the created class before it is inserted into the
    repository.

    This class is private to pywbem_mock
    """
    def __init__(self, faked_conn_object):
        """
        Initialize the connection.

          Parameters:

            conn (BaseRepositoryConnection):
              The underlying repository connection.

              `None` means that there is no underlying repository and all
              operations performed through this object will fail.
        """
        super(_MockMOFWBEMConnection, self).__init__(conn=faked_conn_object)

        # Reassign the variables the represent the repository to the
        # faked_conn_object so that we have a common repository
        self.qualifiers = faked_conn_object.qualifiers
        self.instances = faked_conn_object.instances
        self.classes = faked_conn_object.classes

    def CreateClass(self, *args, **kwargs):
        """
        Override the CreateClass method in MOFWBEMConnection

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """
        cc = args[0] if args else kwargs['NewClass']
        namespace = self.getns()

        try:
            self.compile_ordered_classnames.append(cc.classname)

            # The following generates an exception for each new ns
            self.classes[self.default_namespace][cc.classname] = cc
        except KeyError:
            self.classes[namespace] = \
                NocaseDict({cc.classname: cc})

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

        ccr = self.conn._resolve_class(  # pylint: disable=protected-access
            cc, namespace, self.qualifiers[namespace])
        if namespace not in self.classes:
            self.classes[namespace] = NocaseDict()
        self.classes[namespace][ccr.classname] = ccr

        try:
            self.class_names[namespace].append(ccr.classname)
        except KeyError:
            self.class_names[namespace] = [ccr.classname]

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
