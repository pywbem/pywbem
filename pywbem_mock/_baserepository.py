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
Base classes for an object store for CIM classes, CIM instances, and CIM
qualifier declarations and the generic API for a repository of these object
types organized by repository.

For documentation, see mocksupport.rst.
"""
from abc import ABCMeta, abstractmethod

import six


@six.add_metaclass(ABCMeta)
class ObjectStoreAPI(object):
    """
    This abstract class defines the APIs for the methods of an object store
    for the CIM objects that constitute a WBEM server repository.  This
    class provides the abstract methods for creating, accessing, and deleting,
    CIM objects of a single CIM object type in the repository.
    """

    def __init__(self, case_insensitive_names, cim_object_type):
        """
        Initialize the object store.

        Parameters:

            case_insensitive-names(:class:`py:bool`):
              If True, the names uniquely identify objects in the object store
              case insensitively. The names must be strings.
              If False, names identify objects. The names may be strings
              or other objects that can be used to uniquely identify
              objects in the object store.

            cim_object_type(:term:`string`):
              The Pywbem cim object type as defined in cim_types.py for the
              objects in the data store. Used to verify values on create.
        """
        self._case_insensitive_names = case_insensitive_names
        self._cim_object_type = cim_object_type

    @abstractmethod
    def exists(self, name):
        """
        Test if cim_object defined by name and namespace exists in the
        object store

        Paramsters
          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store

        Returns:
            True if the object exists; False if it does not exist
        """
        pass

    @abstractmethod
    def get(self, name, copy=True):
        """
        Return the cim_object defined by name and namespace if it exists.

        Parameters:
          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store

          copy: If True, insures that modifying the returned object does not
            change the data store

        Returns: The cim_object identified by the name parameter

        Raises:
            KeyError: Object not in this object store
        """
        pass

    @abstractmethod
    def create(self, name, cim_object):
        """
        Insert the cim_object into the object store identified by name.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store .

          cim_object(cim_object to be added to the object store):

        Raises:
            ValueError: If object already in the object store
        """
        pass

    @abstractmethod
    def update(self, name, cim_object):
        """
        Replace the object defined by name in the object store with
        the object defined by cim_object.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store.

          cim_object(cim_object to be added to the object store):

        Raises:
            KeyError: If no object with name exists in this object store

        """
        pass

    @abstractmethod
    def delete(self, name):
        """
        Delete the object identified by name in the object store

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store.

        Raises:
            KeyError: If there is no object with name in this object store

        """
        pass

    @abstractmethod
    def iter_names(self):
        """
        Return iterator to the names of the objects in the object store.

        Returns:
            List of the names of CIM objects in the object store
        """
        pass

    @abstractmethod
    def iter_values(self, copy=True):
        """
        Return iterator to the cim objects in the object store. This allows
        iteration through all the objects in this
        object store. Objects may be accessed using iterator methods.

        Parameters:
          copy (:class:`py:bool`):
            Copy the objects before returning them.  This is the default
            behavior and also the mode that should be used unless the
            user is certain the object will NOT be modified after it is
            returned.

        Returns:
            Python iterator for the object values in the object store.
            If copy == True, each object is copied before it is returned.
        """
        pass

    @abstractmethod
    def len(self):
        """
        Get count of objects in this object store

        Returns:
            Integer that is count of objects in this objectstore

        """
        pass


@six.add_metaclass(ABCMeta)
class BaseRepositoryAPI(object):
    """
    An abstract base class for  the APIs to provide access to a data store for
    a CIM repository.  The API provides functions to:

    1. Manage CIM namespaces in the data repository including creation, deletion
       and getting a list of the available namespaces.
    2. Accessing the object store within the repository for the objects of the
       following CIM types: (CIM classes, CIM instances, and CIM qualifier
       decelarations) so that methods of the ObjStoreAPI can be used to access
       objects by namespace so that CIM objects can be manupulated in the
       repository by namespace.

    """

    # TODO I need to limit the obj store to defined types in API
    # def __init__(self, repository, obj_store):
    # """
    # Construct the repository by defining the namespace with the supplied
    # default_namespace and setting the objects for the classes, instances,
    # and qualifiers
    # """

    # self.repository.classes = obj_store(True, CIMClass)
    # self.repository.instances = obj_store(False, CIMInstance)
    # self.repository.qualifiers = obj_store(True, CIMQualifierDeclaration)

    @abstractmethod
    def validate_namespace(self, namespace):
        """
        Validate if the namespace parameter exists in the repository. If the
        namespace does not exist a KeyError is raised.

        Raises:
            KeyError: If the namespace is not defined in the repository
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def list_namespaces(self):
        """
        List the namespaces that exist in the repository

        Returns:
            list of :term:`string` items containing the namespace names
        """
        pass

    @abstractmethod
    def get_class_repo(self, namespace):
        """
        Get the handle for the data CIM class object store for the namespace
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

        pass

    @abstractmethod
    def get_instance_repo(self, namespace):
        """
        Get the handle for the data CIM instance object store for the namespace
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

    @abstractmethod
    def get_qualifier_repo(self, namespace):
        """
        Gets the handle for the data CIM qualifier declaration object store for
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
