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
"""

from abc import abstractmethod, abstractproperty
from six import add_metaclass
from custom_inherit import DocInheritMeta

import six


def compatibleabstractproperty(func):
    """
    Python 2 and python 3 differ in decorator for abstract property.
    in python 3 (gt 3.3) it is:
        @property
        @abstractproperty
    in python 2
        @abstractproperty
    """

    if six.PY2:  # pylint: disable=no-else-return
        return abstractproperty(func)
    else:
        return property(abstractmethod(func))


@add_metaclass(DocInheritMeta(style="google", abstract_base_class=True))
class BaseObjectStore(object):
    """
    An abstract class that defines the APIs for the methods of an object store
    for CIM objects including CIMClass, CIMInstance, and CIMQualifierDeclaration
    objectsthat constitute a WBEM server repository.  This
    class provides the abstract methods for creating, accessing, and deleting,
    CIM objects of a single CIM object type in the repository.

    These APIs allows creating, updating, deleting, and retrieving these
    objects.
    """

    def __init__(self, cim_object_type):
        """
        Initialize the object store.

        Parameters:

            cim_object_type(:term:`string`):
              The Pywbem cim object type as defined in cim_types.py for the
              objects in the data store. Used to verify values on create.
        """
        self._cim_object_type = cim_object_type

    @abstractmethod
    def exists(self, name):
        """
        Test if cim_object defined by name exists in the
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
            change the data store. The default behavior is True.  If
            copy is False, the object in the object store is returned but
            if it is modified by the user, the object in the store may
            be modified also.

        Returns:

            Returns the cim_object identified by the name parameter

        Raises:

            KeyError: cim_object with name not in this object store
        """
        pass

    @abstractmethod
    def create(self, name, cim_object):
        """
        Adds the cim_object identified by name to the object store.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store .

          cim_object(cim_object to be added to the object store):
            The CIM object that will be inserted into the object store.

        Raises:

            ValueError: If object already exists in the object store.
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

            KeyError: If no object with name exists in the object store.
        """
        pass

    @abstractmethod
    def delete(self, name):
        """
        Delete the object identified by name from the object store.

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
        Return iterator to the names of the objects in the object store.e o

        The order of returned names is undefined.

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

        The order of returned values is undefined.


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
        Get count of objects in this object store.

        Returns:
            Integer that is count of objects in this objectstore

        """
        pass


@add_metaclass(DocInheritMeta(style="google", abstract_base_class=True))
class BaseRepository(object):
    """
    An abstract base class defining the required  APIs to provide access to a
    a CIM repository.  The API provides functions to:

    1. Manage CIM namespaces in the data repository including creation, deletion
       and getting a list of the available namespaces.
    2. Access the object store within the repository for the objects of the
       following CIM types: (CIM classes, CIM instances, and CIM qualifier
       decelarations) so that methods of the BaseObjectStore are used to access
       objects by namespace to manipulate CIM objects in the repository by
       namespace.

    Example :

      xxxrepo = XXXRepository()                        # create the repo
      xxxrepo.add_namespace("root/cimv2")              # add a namespace
      class_repo = xxx.repo.get_class_repo("root/cimv2") # get class obj store
      test_class = CIMClass(...)                       # create a class
      class_repo.add(test_class)                       # add to xxxrepo classes
    """

    @compatibleabstractproperty
    def namespaces(self):
        """
        Read-only property that returns a list with the names of the
        namespaces defined for this repository. Note that if there were any
        leading or trailing slash characters in namespace parameters used
        to add the namespaces to the repository, they will be removed from
        the namespaces returned with this property.

        Returns:
            list of :term:`string` items containing the namespace names
        """
        pass

    @abstractmethod
    def validate_namespace(self, namespace):
        """
        Validate if the namespace exists in the repository. If the
        namespace does not exist a KeyError is raised.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Raises:

          KeyError: If the namespace is not defined in the repository.
          ValueError: if the namespace is None.
        """
        pass

    @abstractmethod
    def add_namespace(self, namespace):
        """
        Add a CIM namespace to the repository.

        The namespace must not yet exist in the CIM repository.

        The default connection namespace is automatically added to
        the CIM repository upon creation of this connection.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

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
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Raises:

          ValueError: Namespace argument is None or the repository namespace
            is not empty
          KeyError:  The namespace does not exist in the CIM repository.
        """
        pass

    @abstractmethod
    def get_class_repo(self, namespace):
        """
        Get the handle for the data CIM class object store for the namespace
        provided.

        Parameters:
          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Returns:

          Returns the instance of :class:`~pywbem_mock.InMemoryObjectStore` for
          CIM classes which defines the methods exists(name), get(name)
          create(), etc. for accessing the data in this store.

        Raises:

          ValueError: Namespace argument is None.
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
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Returns:

          Returns the instance of :class:`~pywbem_mock.InMemoryObjectStore`
          for CIM instances which defines the methods exists(), get() create(),
          etc. for accessing the data in this store.

        Raises:

          ValueError: Namespace argument is None.
          KeyError: The namespace parameter does not define an existing
            namespace
        """

    @abstractmethod
    def get_qualifier_repo(self, namespace):
        """
        Gets the handle for the data CIM qualifier declaration object store for
        the namespace provided.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Returns:

          Returns the instance of :class:`~pywbem_mock.InMemoryObjectStore` for
          CIM qualifier declarations which defines the methods exists(), get()
          create(), etc. for accessing the data in this store.

        Raises:

          ValueError: Namespace parameter is None
          KeyError: The namespace parameter does not define an existing
            namespace
        """
