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
Base abstract classes for an object store for collections of
:class:`~pywbem.CIMClass`, :class:`~pywbem.CIMInstance`, and
:class:`~pywbem.CIMQualifierDeclaration` objects and a generic API for a CIM
repository to access and manage the collections of each of these CIM object
types.

The repository is organized by namespace such that a namespace must be created
before it can be used to contain CIM object collections and each namespace
contains an object store for each CIM object type containing the CIM objects
that have been added to the CIM repository.

Example :

.. code-block:: python

    # MyRepository is a class derived from BaseRepository
    repo = MyRepository()                            # create the repo
    repo.add_namespace("root/cimv2")                 # add a namespace
    class_store = .repo.get_class_store("root/cimv2") # get class obj store
    test_class = CIMClass('CIM_Blah', ...)           # create a class
    class_store.add(test_class)                      # add to xxxrepo classes
    if 'CIM_Blah' in class_store:                    # test if class exists
        klass = class_store.get('CIM_Blah;)          # get the class
"""

from abc import abstractmethod, abstractproperty
from six import add_metaclass, PY2
from custom_inherit import DocInheritMeta


def compatibleabstractproperty(func):
    """
    Python 2 and python 3 differ in decorator for abstract property.
    in python 3 (gt 3.3) it is:
        @property
        @abstractproperty
    in python 2
        @abstractproperty
    """

    if PY2:  # pylint: disable=no-else-return
        return abstractproperty(func)
    else:
        return property(abstractmethod(func))


@add_metaclass(DocInheritMeta(style="google", abstract_base_class=True))
class BaseObjectStore(object):
    """
    An abstract class that defines the APIs for the methods of an object store
    for CIM objects including CIMClass, CIMInstance, and CIMQualifierDeclaration
    objects that constitute a WBEM server repository.  This
    class provides the abstract methods for creating, accessing, and deleting,
    CIM objects of a single CIM object type in the repository.

    CIM objects in the object store are identified by a name which is part of
    the methods that access the CIM objects and must be unique within a single
    object store.

    Each object store conatins only a single CIM object type.
    """

    @abstractmethod
    def __init__(self, cim_object_type):
        """
        Instantiate the self.cim_object_type variable.

        Parameters:

          cim_object_type (:term:`CIM object`):
            The Pywbem CIM object type as defined in cim_types.py for the
            objects in the data store. Used to verify values on create.
        """
        self._cim_object_type = cim_object_type

    @abstractmethod
    def object_exists(self, name):
        """
        Test if the CIM object identified by name exists in the object store.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store.

        Returns:

            :class:`py:bool`: Indicates whether the CIM object exists in the
            object store.
        """
        pass

    @abstractmethod
    def get(self, name, copy=True):
        """
        Return the CIM object identified by name if it exists in the object
        store.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store

          copy(:class:`py:bool`):
            If True, returns a copy of the object to insure that modifying the
            returned object does not change the data store. The default
            behavior is True .  If copy is False, the object in the object
            store is returned but if it is modified by the user, the object in
            the store may be modified also.

        Returns:

            :term:`CIM object`: Returns the CIM object identified by the
            name parameter.

        Raises:

            KeyError: CIM object identified with name not in the object store
        """
        pass

    @abstractmethod
    def create(self, name, cim_object):
        """
        Add the CIM object to the object store.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the CIM object will be identified in the object store.

          cim_object(:term:`CIM object`):
            The CIM object to be added to the object store. The
            object is copied into the object store so the user can safely
            modify the original object without affecting the store.

        Raises:

            ValueError: If CIM object already exists in the object store.
        """
        pass

    @abstractmethod
    def update(self, name, cim_object):
        """
        Replace the CIM object in the object store idenfified by the name
        argument with the CIM object defined by the cim_object argument.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object is identified in the object store.

          cim_object(:term:`CIM object`):
            The CIM object to replace the original CIM object in the data
            store. The object is copied into the object store so the user can
            safely modify the original object without affecting the store.

        Raises:

            KeyError: If no CIM object with name exists in the object store.
        """
        pass

    @abstractmethod
    def delete(self, name):
        """
        Delete the CIM object identified by name from the object store.

        Parameters:

          name(:term:`string` or :class:`~pywbem.CIMInstanceName`):
            Name by which the object to be deleted is identified in the object
            store.

        Raises:

            KeyError: If there is no object with name in this object store
        """
        pass

    @abstractmethod
    def iter_names(self):
        """
        Return an iterator to the names of the CIM objects in the object store.
        Objects may be accessed using iterator methods.

        The order of returned names is undetermined.

        Returns:

            :term:`iterator`: An iterator for the names of CIM objects in the
            object store.
        """
        pass

    @abstractmethod
    def iter_values(self, copy=True):
        """
        Return an iterator to the CIM objects in the object store. This allows
        iteration through all the objects in this object store using iterator
        methods.

        The order of returned CIM objects is undetermined.

        Parameters:

          copy (:class:`py:bool`):
            Copy the objects before returning them.  This is the default
            behavior and also the mode that should be used unless the
            user is certain the object will NOT be modified after it is
            returned.

        Returns:

            :term:`iterator`: An iterator for the objects in the object
            store. If copy == True, each object is copied before it is
            returned.
        """
        pass

    @abstractmethod
    def len(self):
        """
        Return the count of objects in this object store.

        Returns:

            int: Integer that is count of objects in this object store.
        """
        pass


@add_metaclass(DocInheritMeta(style="google", abstract_base_class=True))
class BaseRepository(object):
    """
    An abstract base class defining the required  APIs to provide access to a
    a CIM repository.  The API provides functions to:

    1. Manage CIM namespaces in the data repository including creation, deletion
       and getting a list of the existing namespaces.
    2. Access the object store for each CIM object type in the repository for
       the objects of the following CIM types: (:class:`~pywbem.CIMClass`,
       :class:`~pywbem.CIMInstance`, and
       :class:`~pywbem.CIMQualifierDeclaration`)
       so that methods of the BaseObjectStore are used to access and manipulate
       CIM objects of a single CIM type by namespace in the repository.
    """

    @compatibleabstractproperty
    def namespaces(self):
        """
        Read-only property that returns a list with the names of the
        namespaces existing in this repository. Note that if there were any
        leading or trailing slash ("/") characters in namespace parameters used
        to add the namespaces to the repository, they will be removed from
        the namespaces returned with this property.

        Returns:

            list of :term:`string`: List containing the namespace names in this
            repository.
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
            is not empty.
          KeyError:  Namespace does not exist in the CIM repository.
        """
        pass

    @abstractmethod
    def get_class_store(self, namespace):
        """
        Return the CIM class object store for the namespace provided.

        Parameters:
          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Returns:

          :class:`~pywbem_mock.InMemoryObjectStore` : CIM class object store
          for the namespace provided.

        Raises:

          ValueError: Namespace argument is None.
          KeyError: Namespace does not exist in the repository
        """

        pass

    @abstractmethod
    def get_instance_store(self, namespace):
        """
        Return the CIM instance object store for the namespace provided.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Returns:

          :class:`~pywbem_mock.InMemoryObjectStore`: CIM instance object store
          for the namespace provided.

        Raises:

          ValueError: Namespace argument is None.
          KeyError: Namespace argument does exist in the repository.
        """

    @abstractmethod
    def get_qualifier_store(self, namespace):
        """
        Return the  CIM qualifier declaration object store for the namespace
        provided.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. The name is
            treated case insensitively and it must not be `None`. Any leading
            and trailing slash characters in the namespace string are ignored
            when accessing the repository.

        Returns:

          :class:`~pywbem_mock.InMemoryObjectStore`: CIM qualifier declaration
          object store for the namespace provided.

        Raises:

          ValueError: namespace parameter is None
          KeyError: namespace argument does exist in therepository.
        """
