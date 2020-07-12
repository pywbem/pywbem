#
# (C) Copyright 2020 InovaDevelopment.com
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
The MethodProvider module adds support for user-defined method providers.  User
defined method providers may be created within pywbem_mock to extend the
capability of the mocker for processing methods defined in CIM classes using
WBEM extrensic methods (the `InvokeMethod` client request).

Since there is no concept of a default method provider (all CIM methods imply
actions that are specific to the method), the default method provider always
returns an exception (CIM_ERR_NOT_FOUND).

User defined providers may be created for specific CIM classes and namespaces
to override the InvokeMethod in :class:`~pywbem_mock.MethodProvider` with user
methods defined in a subclass of :class:`~pywbem_mock.MethodProvider`.

This module contains the default MethodProvider class which provides the
following:

1. Definition of the provider type (``provider_type = "method"``).
2. Definition of the API and return for the ``InvokeMethod`` method required in
   the user-defined subclass.

A user-defined method provider can be created as follows:

1. Implement the subclass of :class:`~pywbem_mock.MethodProvider` with:

   a. Constructor:
      `__init__()` that takes as input at least the cimrepository
      object parameter and passes it to the superclass and any other
      constructor parameters the user-defined provider requires.  Since the
      user creates the instance.

      .. code-block:: python

         def __init__(self, cimrepository):
             super(UserMethodTestProvider, self).__init__(cimrepository)

   b. Definition of the CIM class the provider supports as a class variable.

      .. code-block:: python

        provider_classnames = 'CIM_Foo'

   c. Definition and implementation of the WBEM operations supported by the
      provider from the set of request operations defined in the table above
      for a specific provider type. This must be a subset of the methods
      defined for the provider type. Methods that do not exist in the
      user-defined provider default to the default method. Each of these
      methods may:

      * provide parameter or cim repository validation in addition to the normal
        request validation,
      * modify parameters of the request.
      * generate an CIMError exception for the operation.
      * make modifications to the cim repository.

      The request may be completed by the user provider method calling the
      superclass corresponding method to complete its final validation and
      modify the repository or by the provider directly modifying the repository
      based on the method and parameters.

      The user-defined providers have access to:
        * methods defined in their superclass
        * methods defined in :class:~pywbem_mock.BaseProvider`
        * methods to access the CIM repository using the methods defined in
          :class:`~pywbem_mock.InMemoryRepository`

      .. code-block:: python

        def CreateInstance(self, namespace, NewInstance):
            \"\"\"Test Create instance just calls super class method\"\"\"

            # Simply calls the default responder method for CreateInstance
            return super(UserInstanceTestProvider, self).CreateInstance(
                namespace, NewInstance)

   d. Optional method
      The provider may include
      (:meth:`~pywbem_mock.MethodProvider.post_register-setup()`) that
      :meth:`~pywbem_mock.FakedWBEMConnection.register_provider` will call as
      after the provider registration is successful.  This allows the provider
      to do any special setup it desires uses its own methods. This method
      includes the current connection as a parameter so that client methods can
      be executed directly.

      .. code-block:: python

          def post_register_setup(self, conn):
            # code that performs post registration setup for the provider


   The input parameters for the user defined invoke_method InvokeMethod will
   have been already validated in
   :class:`~pywbem_mock.ProviderDispatcher.ProviderDispatcher` including:

   a. The namespace defined in the namespace parameter exists.
   b. The classname defined in the ObjectName parameter exists in the
      namespace.
   c. The method defined in the MethodName parameter exists.
   d. The method provider is registered for this classname in this namespace.

   The correspondence between parameters in the ``Params`` argument and in
   the class have not been verified.

   The created method should implement any exceptions based on
   :class:`pywbem.CIMError` (as a server would) using the error codes defined
   in :term:`DSP0200` which will be passed back to the client.

   Thus, a user-defined method provider defines a subclass to
   :class:`~pywbem_mock.MethodProvider and defines a `InvokeMethod` method in
   the user-defined subclass to override
   :meth:`~pywbem_mock.MethodProvider.InvokeMethod`.

   The user-defined provider has access to:
       * methods defined in the superclass :class:~pywbem_mock.MethodProvider`
       * methods defined in :class:~pywbem_mock.BaseProvider`
       * methods to access the CIM repository using the methods defined in
         :class:`~pywbem_mock.InMemoryRepository`

2. Register the user-defined method provider using
   :meth:`~pywbem_mock.FakedWBEMConnection.register_provider` to define the
   namespaces for which the user provider will override
   :class:`~pywbem_mock.InstanceWriteProvider`.  The registration of the user
   provider must occur after the namespaces defined in the registration have
   been added to the CIM repository.
"""

from __future__ import absolute_import, print_function

from pywbem import CIMError, CIM_ERR_METHOD_NOT_FOUND

from ._baseprovider import BaseProvider

# None of the request method names conform since they are camel case
# pylint: disable=invalid-name

__all__ = ['MethodProvider']


class MethodProvider(BaseProvider):
    """
    This class defines the provider class that handles the default InvokeMethod.

    User  method providers are defined by creating a subclass of this class and
    defining an InvokeMethod based on the method in this class.
    """
    #:  provider_type (:term:`string`):
    #:    Keyword defining the type of request the provider will service.
    #:    The type for this class is predefined as 'method'
    provider_type = 'method'

    def __init__(self, cimrepository=None):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the repository to be used by request responders.
        """
        super(MethodProvider, self).__init__(cimrepository)

    ####################################################################
    #
    #   InvokeMethod mock WBEM server responder
    #
    ####################################################################

    def InvokeMethod(self, methodname, localobject, params):
        # pylint: disable=invalid-name,no-self-use
        # pylint: disable=line-too-long
        """
        Implements a mock WBEM server responder for
        :meth:`pywbem.WBEMConnection.InvokeMethod`.

        Invoke a CIM method (static or dynamic) on a target CIM object (class or
        instance) in the CIM repository of the mock WBEM server.

        This default provider always raises CIMError(CIM_ERR_METHOD_NOT_FOUND)
        because there is no concept of a default method invocation behavior in
        in CIM (other than raising this error). A user-defined method provider
        is necessary to have a meaningful implementation of a method invocation.

        Validation already performed by the provider dispatcher that calls
        this provider method:
        - The provider method is called only for the registered class and
          namespace (only applies to user-defined providers).
        - The Python types of all input parameters to this provider method are
          as specified below.
        - The namespace exists in the CIM repository.
        - For instance-level use:
          - The creation class of the target instance exists in the namespace
            of the CIM repository.
          - The target instance exists in the namespace of the CIM repository.
          - The creation class of the target instance exposes the method to be
            invoked.
        - For class-level use:
          - The target class exists in the namespace of the CIM repository.
          - The target class exposes the method to be invoked.
          - The method exposed by the creation class is a static method
            as per its 'Static' qualifier.
        - The set of specified CIM method input parameters matches exactly the
          set of input parameters defined by the method in the CIM repository
          (as detected by their 'In' qualifier in the creation class), w.r.t.
          parameter name and type-related attributes (type, is_array,
          embedded_object).

        Validation that should be performed by this provider method:

        - MethodName is the name of a method the provider implements.
        - Constraints on the values of input parameters.

        Parameters:

          methodname (:term:`string`):
            Name of the CIM method to be invoked, in any lexical case.

          objectname: (:class:`~pywbem.CIMInstanceName` or :class:`~pywbem.CIMClassName`):
            A reference to the target CIM object, as follows:

            * For instance-level use: The instance path of the target
              instance, as a :class:`~pywbem.CIMInstanceName` object, with the
              following attributes:
              - `classname`: Will be set, in any lexical case.
              - `keybindings`: Will be set, with key names in any lexical case.
              - `namespace`: Will be set, in any lexical case, and with leading
                and trailing slash characters removed.
              - `host`: Will be `None`.

            * For class-level use: The class path of the target class, as a
              :class:`~pywbem.CIMClassName` object, with the following
              attributes:
              - `classname`: Will be set, in any lexical case.
              - `namespace`: Will be set, in any lexical case, and with leading
                and trailing slash characters removed.
              - `host`: Will be `None`.

          params (:class:`py:NocaseDict`):
            The input parameters for the method invocation, with items as
            follows:
            - key (:term:`string`): The parameter name, in any lexical case.
            - value (:class:`~pywbem.CIMParameter`): The parameter value.

        Returns:

            :func:`py:tuple` (return_value, out_params): The return value and
            output parameters of the method invocation:

            * return_value (:term:`CIM data type`):
              Return value of the method invocation.

            * out_params (list/tuple or dict):
              Output parameters of the method invocation.

              If list/tuple, the items must be :class:`~pywbem.CIMParameter`
              in any order, with these attributes set:
                * name (:term:`string`): Parameter name
                * value (:term:`CIM data type`): Parameter value

              If dict, the items must be as follows:
                * key (:term:`string`): Parameter name
                * value (:term:`CIM data type`): Parameter value

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_METHOD_NOT_FOUND) because the
              default method is only a placeholder for the API and
              documentation and not a real InvokeMethod action implementation.
        """  # noqa: E501
        # pylint: enable=line-too-long

        # There is no concept of a default method invocation behavior in CIM
        raise CIMError(CIM_ERR_METHOD_NOT_FOUND)

    def post_register_setup(self, conn):
        """
        Method called by provider registration after registation of provider
        is successful. Using this method is optional for registration cases
        where the provider must execute some activity (ex. modify the
        CIM repository after successful provider registration).

        Override this method in the user-defined provider subclass to execute
        this method.

        Parameters:

          conn (:class:`~pywbem.WBEMConnection`):
            Current connection which allows client methods to be executed
            from within this method.
        """
        pass
