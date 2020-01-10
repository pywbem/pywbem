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
Implementation of the BaseRepository abstract classes that defines an in-memory
repository based on dictionaries.
"""

import six

from pywbem._nocasedict import NocaseDict

from pywbem import CIMClass, CIMQualifierDeclaration, CIMInstance
from pywbem._utils import _format
from ._baserepository import ObjectStoreAPI, BaseRepositoryAPI


class InMemoryObjStore(ObjectStoreAPI):
    """
    Derived from the :class:`ObjectStoreAPI`, this class implements a
    dictionary based in-memory repository for CIM objects that manages
    CIM classes, CIM instances, and CIM qualifier declarations.
    """

    def __init__(self, case_insensitive_names, cim_object_type):
        """
          Parameters:

            case_insensitive_names(:class:`py:bool`):
                Defines whether the data store for this type handles
                case insesitive names or not

            cim_object_type ():
             CIMType of the object stored in this object store. Only CIMClass,
             CIMInstance, and CIMQualifierDeclaration types are allowed.
        """

        self._case_insensitive_names = case_insensitive_names
        self._cim_object_type = cim_object_type

        self._data = NocaseDict() if case_insensitive_names else {}

    def __repr__(self):
        return _format('InMemoryObjStore(type={0},  dict={1}, size {2}',
                       self._cim_object_type, type(self._data),
                       len(self._data))

    def exists(self, name):
        """
        Overrides the abstract method.

        Returns boolean True if the object is in the dictionary. Otherwise
        returns False
        """
        return True if name in self._data else False

    def get(self, name, copy=True):
        """
        Overrides the abstract method.

        Gets the object with name from the dictionary or returns an exception
        if an object with name does note exist.

        If copy is True, it generates creates a copy and returns the copy
        """

        if name in self._data:
            if copy:
                return self._data[name].copy()
            return self._data[name]
        else:
            raise KeyError('{} not in {} object store'
                           .format(name, self._cim_object_type))

    def create(self, name, cim_object):
        """
        Overrides the abstract method.

        Creates a new cim_object in the object store dictionary or fails
        with an exception if the name already exists in the dictionary.
        """

        assert isinstance(cim_object, self._cim_object_type)

        if name in self._data:
            raise ValueError('{} already in {} object store'
                             .format(name, self._cim_object_type))

        self._data[name] = cim_object.copy()

    def update(self, name, cim_object):
        """
        Overrides the abstract method.

        This method updates the corresponding dictionary with the cim_object
        if the object exists in the dictionary. Otherwise it returns
        an exception.

        """

        assert isinstance(cim_object, self._cim_object_type)

        if name not in self._data:
            raise KeyError('{} not in {} object store'
                           .format(name, self._cim_object_type))

        # Replace the existing object with a copy of the input object
        self._data[name] = cim_object.copy()

    def delete(self, name):
        """
        Overrides the abstract method.

        If the object exists in the object store dictionary, it is deleted.
        If it does not exist an exception is returned.
        """
        if name in self._data:
            del self._data[name]
        else:
            raise KeyError('{} not in {} object store'
                           .format(name, self._cim_object_type))

    def iter_names(self):
        """
        Overrides the abstract method.

        Returns iterator for names of the objects in the object store

        """
        return six.iterkeys(self._data)

    def iter_values(self, copy=True):
        """
        Overrides the abstract method.

        Returns an iterator for the object values in the object store
        """
        if copy:
            for value in six.itervalues(self._data):
                yield(value.copy())
        else:
            return six.itervalues(self._data)

    def len(self):
        """
        Overrides the abstract method
        :class:`~pywbem_mock._baserepository.ObjectStoreAPI.len`

        Returns count of number of objects in the object store dictionary.
        """
        return len(self._data)


class InMemoryRepository(BaseRepositoryAPI):
    """
    Defines the data store and access methods for a simple CIMClass,
    CIMInstance, and CIMQualifierDeclaration repository that maintains the date
    in memory.

    The API for this data store is defined in the BaseRepositoryAPI class and
    the ObjectStoreAPI class.
    """
    def __init__(self, initial_namespace):
        """
        Initialize the InMemoryRepository by creatiing the initial
        namespace definition and the data stores for CIM classes, CIM instances,
        and CIM qualifier declarations.

          Parameters:
             Initial namespace defined for this repository
        """

        # Create the in memory repository.  This defines the top level
        # NocaseDict which defines the namespaces.
        self._repository = NocaseDict()

        # Create the initial namespace
        self.add_namespace(initial_namespace)
        namespace = initial_namespace.strip('/')

        # Create the object store for each the CIM types to be stored
        self._repository[namespace]['classes'] = InMemoryObjStore(
            True, CIMClass)
        self._repository[namespace]['instances'] = InMemoryObjStore(
            False, CIMInstance)
        self._repository[namespace]['qualifiers'] = InMemoryObjStore(
            True, CIMQualifierDeclaration)

    def print(self):
        """
        Display the items in the repository. This displays information on
        the items in the data base
        """
        def repo_info(repo_name):
            for ns in self._repository.keys():
                if repo_name == 'class':
                    repo = self.get_class_repo(ns)
                elif repo_name == 'qualifier':
                    repo = self.get_qualifier_repo(ns)
                elif repo_name == 'instance':
                    repo = self.get_instance_repo(ns)
                else:
                    assert False
                rtn_str = 'Namespace: {} Repo: {} len:{}\n'.format(ns,
                                                                   repo_name,
                                                                   repo.len())
                for val in repo.iter_values():
                    rtn_str += ('{}\n'.format(val))
                return rtn_str

        print('NAMESPACES: {}'.format(self._repository.keys()))

        print('QUALIFIERS: {}'.format(repo_info('qualifier')))
        print('CLASSES: {}'.format(repo_info('class')))
        print('INSTANCES: {}'.format(repo_info('instance')))

    def validate_namespace(self, namespace):
        """
        Validate if the namespace existsin the repository. If the namespace
        does not exist a KeyError is raised.

        Raises:
            KeyError: If the namespace is not defined in the repository
        """

        namespace = namespace.strip('/')
        try:
            self._repository[namespace]
        except KeyError:
            raise

    def add_namespace(self, namespace):
        """
        Add a CIM namespace to the repository.

        The namespace must not yet exist in the mock repository.

        The default connection namespace is automatically added to
        the mock repository upon creation of this connection.

          Parameters:
            namespace (:term:`string`):
              The name of the CIM namespace in the mock repository. Must not be
              `None`. Leading and trailing slash characters are split off
              from the provided string.

          Raises:
            ValueError: If the namespace argument is None or the
             namespace already exists.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        namespace = namespace.strip('/')

        if namespace in self._repository:
            raise ValueError('Namespace {} already nn repository'.
                             format(namespace))

        self._repository[namespace] = {}

        # Create the data store for each of the object types.
        self._repository[namespace]['classes'] = InMemoryObjStore(
            True, CIMClass)

        self._repository[namespace]['instances'] = InMemoryObjStore(
            False, CIMInstance)

        self._repository[namespace]['qualifiers'] = InMemoryObjStore(
            True, CIMQualifierDeclaration)

    def remove_namespace(self, namespace):
        """
        Remove a CIM namespace from the repository.

        The namespace must exist in the repository and must be empty.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the mock repository. Must not be
            `None`. Any leading and trailing slash characters are split off
            from the provided string.

        Raises:

          ValueError: Namespace argument is None or the repository namespace
            is not empty
          KeyError:  The namespace does not exist in the mock repository.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        namespace = namespace.strip('/')

        if namespace not in self._repository:
            raise KeyError("Invalid namespace name {}".format(namespace))

        if self.get_class_repo(namespace).len() != 0 or \
                self.get_qualifier_repo(namespace).len() != 0 or \
                self.get_instance_repo(namespace).len() != 0:
            raise ValueError('Namespace {} removal invalid. Namespace not '
                             'empty'.format(namespace))

        del self._repository[namespace]

    # TODO: Why not make this a property
    def list_namespaces(self):
        """
        List the namespaces that exist in the repository

        Returns:
            list of :term:`string` items containing the namespace names
        """
        return self._repository.keys()

    def get_class_repo(self, namespace):
        """
        Get the handle for the data CIM class data store for the namespace
        provided.

          Parameters:
            namespace (:term:`string`):
              The name of the CIM namespace in the mock repository. Must not be
              `None`

          Returns:
            Returns an instance of InMemoryObjStore which defines the
            methods exists(), get() create(), etc. for accessing the
            data in this store.

          Raises:
            KeyError: If the namespace does not exist in the repository
        """

        if namespace is None:
            raise ValueError("Namespace None not permitted.")
        namespace = namespace.strip('/')
        self.validate_namespace(namespace)
        return self._repository[namespace]['classes']

    def get_instance_repo(self, namespace):
        """
        Get the handle for the data CIM instance data store for the namespace
        provided.

          Parameters:

            namespace (:term:`string`):
              The name of the CIM namespace in the mock repository. Must not be
              `None`
          Returns:
            returns an instance of InMemoryObjStore which defines the
            methods exists(), get() create(), etc. for accessing the
            data in this store.
        """

        if namespace is None:
            raise ValueError("Namespace None not permitted.")
        namespace = namespace.strip('/')
        self.validate_namespace(namespace)
        return self._repository[namespace]['instances']

    def get_qualifier_repo(self, namespace):
        """
        Gets the handle for the data CIM qualifier declaration data store for
        the namespace provided.

          Parameters:

            namespace (:term:`string`):
              The name of the CIM namespace in the mock repository. Must not be
              `None`
          Returns:
            returns an instance of InMemoryObjStore which defines the
            methods exists(), get() create(), etc. for accessing the
            data in this store.

          Raises:
            ValueError if namespace parameter is None
            KeyError if the namespace parameter does not define an existing
              namespace
        """

        if namespace is None:
            raise ValueError("Namespace None not permitted.")
        namespace = namespace.strip('/')
        self.validate_namespace(namespace)
        return self._repository[namespace]['qualifiers']
