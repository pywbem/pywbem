#
# (C) Copyright 2020 InovaDevelopment.comn
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
The class :class:`~pywbem_mock.InMemoryRepository` implements a CIM repository
that stores the CIM objects in memory. It contains an object store
(:class:`~pywbem_mock.InMemoryObjectStore`) for each type of CIM object
(classes, instances, qualifier declarations) and for each CIM namespace in the
repository. Each object store for a CIM object type contains the CIM objects
of that type in a single CIM namespace.

The CIM repository of a mock WBEM server represented by a
:class:`~pywbem_mock.FakedWBEMConnection` object is a
:class:`~pywbem_mock.InMemoryRepository` object that is created and destroyed
automatically when the
:class:`~pywbem_mock.FakedWBEMConnection` object is created and destroyed.

The CIM repository of a mock WBEM server is accessible through its
:attr:`pywbem_mock.FakedWBEMConnection.cimrepository` property.
"""

from __future__ import absolute_import, print_function

from copy import deepcopy
import six
from nocaselist import NocaseList

from pywbem import CIMClass, CIMQualifierDeclaration, CIMInstance

from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format

from ._baserepository import BaseObjectStore, BaseRepository
from ._utils import _uprint

__all__ = ['InMemoryRepository', 'InMemoryObjectStore']


class InMemoryObjectStore(BaseObjectStore):
    """
    A store for CIM objects of a single type (CIM classes, CIM instances,
    or CIM qualifier declarations) that maintains its data in memory.

    *New in pywbem 1.0 as experimental and finalized in 1.2.*
    """
    # Documentation for the methods and properties inherited from
    # ~pywbem_mock:`BaseObjectStore` is also inherited in the pywbem
    # documentation. Therefore the methods in this class that are derived
    # from abstrace methods have no documentation string.

    # pylint: disable=line-too-long
    def __init__(self, cim_object_type):

        super(InMemoryObjectStore, self).__init__(cim_object_type)

        self._copy_names = False

        # Define the dictionary that implements the object store.
        # The keys in this dictionary are the names of the objects and
        # the values the corresponding CIM objects.
        if cim_object_type.__name__ in ("CIMClass", 'CIMQualifierDeclaration'):
            self._data = NocaseDict()
        elif cim_object_type.__name__ == 'CIMInstance':
            self._data = {}
            self._copy_names = True
        else:
            assert False, "InMemoryObjectStore: Invalid input parameter {}." \
                .format(cim_object_type)

    def __repr__(self):
        return _format('InMemoryObjectStore(type={0},  dict={1}, size={2}',
                       self._cim_object_type, type(self._data),
                       len(self._data))

    def object_exists(self, name):
        return name in self._data

    def get(self, name, copy=True):
        """
        Get with deepcopy because the pywbem .copy is only middle level and
        we need to completely isolate the repository.
        """
        # pylint: disable=no-else-return
        if name in self._data:
            if copy:
                return deepcopy(self._data[name])
            return self._data[name]
        else:
            raise KeyError('Name {} not in {} object store'
                           .format(name, self._cim_object_type))

    def create(self, name, cim_object):
        assert isinstance(cim_object, self._cim_object_type)

        if name in self._data:
            raise ValueError('Name "{}" already in {} object store'
                             .format(name, self._cim_object_type))
        # Add with deepcopy to completely isolate the copy in the repository
        self._data[name] = deepcopy(cim_object)

    def update(self, name, cim_object):
        assert isinstance(cim_object, self._cim_object_type)

        if name not in self._data:
            raise KeyError('Name "{}" not in {} object store'
                           .format(name, self._cim_object_type))

        # Replace the existing object with a copy of the input object
        self._data[name] = (cim_object)

    def delete(self, name):
        if name in self._data:
            del self._data[name]
        else:
            raise KeyError('Name "{}" not in {} object store'
                           .format(name, self._cim_object_type))

    def iter_names(self):
        """
        Only copies the names for those objects that use CIMNamespaceName
        as the name. The others are immutable ex. classname.
        """
        for name in six.iterkeys(self._data):
            if self._copy_names:
                # Using .copy is sufficient for CIMNamespace name.
                yield(name.copy())
            else:
                yield(name)

    def iter_values(self, copy=True):
        for value in six.itervalues(self._data):
            if copy:
                yield(deepcopy(value))
            else:
                yield(value)

    def len(self):
        return len(self._data)


class InMemoryRepository(BaseRepository):
    """
    A CIM repository that maintains the data in memory using the
    methods defined in its superclass (~pywbem_mock:`BaseObjectStore`).

    *New in pywbem 1.0 as experimental and finalized in 1.2.*

    This implementation creates the repository as multi-level dictionary
    elements to define the namespaces and within each
    namespace the CIM classes, CIM instances, and CIM qualifiers in the
    repository.
    """
    # Documentation for the methods and properties  isinherited from
    # ~pywbem_mock:`BaseObjectStore` by sphinx when building documentaton.
    # Therefore the methods in this class have no documentation
    # string unless they add or modify documentation in the parent class or
    # are not defined in the parent class. Any method that needs to modifyu
    # the base method documentation must copy the base class documentation.

    def __init__(self, initial_namespace=None):
        """
        Initialize an empty in-memory CIM repository and optionally add a
        namespace in the repository..

        Parameters:

          initial_namespace:(:term:`string` or None):
            Optional initial namespace that will be added to
            the CIM repository.
        """

        # Defines the top level NocaseDict() which defines the
        # namespaces in the repository. The keys of this dictionary
        # are namespace names and the values are dictionaries
        # defining the CIM classes, CIM instances, and CIM qualifier
        # declarations where the keys are "classes", "instances", and
        # "qualifiers" and the value for each is an instance of the
        # class InMemoryObjectStore that containe the CIM objects.
        self._repository = NocaseDict()

        # If an initial namespace is defined, add it to the repository
        if initial_namespace:
            self.add_namespace(initial_namespace)

    def __repr__(self):
        """Display summary of the repository"""
        return _format(
            "InMemoryRepository(data={s._repository})", s=self)

    def print_repository(self, dest=None, ):
        """
        Print the CIM repository to a destination. This displays information on
        the items in the data base and is only a diagnostic tool.

        Parameters:
          dest (:term:`string`):
            File path of an output file. If `None`, the output is written to
            stdout.
        """
        def objstore_info(objstore_name):
            """
            Display the data for the object store
            """
            for ns in self._repository:
                if objstore_name == 'class':
                    store = self.get_class_store(ns)
                elif objstore_name == 'qualifier':
                    store = self.get_qualifier_store(ns)
                else:
                    assert objstore_name == 'instance'
                    store = self.get_instance_store(ns)

                rtn_str = u'Namespace: {} Repo: {} len:{}\n'.format(
                    ns, objstore_name, store.len())
                for val in store.iter_values():
                    rtn_str += (u'{}\n'.format(val))
                return rtn_str

        namespaces = ",".join(self._repository.keys())
        _uprint(dest, _format(u'NAMESPACES: {0}', namespaces))
        _uprint(dest, _format(u'QUALIFIERS: {0}', objstore_info('qualifier')))
        _uprint(dest, _format(u'CLASSES: {0}', objstore_info('class')))
        _uprint(dest, _format(u'INSTANCES: {0}', objstore_info('instance')))

    def validate_namespace(self, namespace):
        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        namespace = namespace.strip('/')
        try:
            self._repository[namespace]
        except KeyError:
            raise KeyError('Namespace "{}" does not exist in repository'.
                           format(namespace))

    def add_namespace(self, namespace):
        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        namespace = namespace.strip('/')

        if namespace in self._repository:
            raise ValueError('Namespace "{}" already in repository'.
                             format(namespace))

        self._repository[namespace] = {}

        # Create the data store for each of the object types.
        self._repository[namespace]['classes'] = InMemoryObjectStore(CIMClass)

        self._repository[namespace]['instances'] = InMemoryObjectStore(
            CIMInstance)

        self._repository[namespace]['qualifiers'] = InMemoryObjectStore(
            CIMQualifierDeclaration)

    def remove_namespace(self, namespace):
        self.validate_namespace(namespace)
        namespace = namespace.strip('/')

        if self.get_class_store(namespace).len() != 0 or \
                self.get_qualifier_store(namespace).len() != 0 or \
                self.get_instance_store(namespace).len() != 0:
            raise ValueError('Namespace {} removal invalid. Namespace not '
                             'empty'.format(namespace))

        del self._repository[namespace]

    @property
    def namespaces(self):
        # pylint: disable=invalid-overridden-method
        # This puts just the dict keys (i.e. namespaces) into the list
        return NocaseList(self._repository)

    def get_class_store(self, namespace):
        if namespace is None:
            raise ValueError("Namespace None not permitted.")
        namespace = namespace.strip('/')
        self.validate_namespace(namespace)
        return self._repository[namespace]['classes']

    def get_instance_store(self, namespace):
        if namespace is None:
            raise ValueError("Namespace None not permitted.")
        namespace = namespace.strip('/')
        self.validate_namespace(namespace)
        return self._repository[namespace]['instances']

    def get_qualifier_store(self, namespace):
        if namespace is None:
            raise ValueError("Namespace None not permitted.")
        namespace = namespace.strip('/')
        self.validate_namespace(namespace)
        return self._repository[namespace]['qualifiers']

    def load(self, other):
        """
        Replace the data in this object with the data from the other object.

        This is used to restore the object from a serialized state, without
        changing its identity.
        """
        # pylint: disable=protected-access
        self._repository = other._repository
