"""
This module adds support for user-defined method providers.  User defined
method providers may be created within pywbem_mock to extend the capability
of the mocker for special processing for selected classes using CIM
extrensic methods (the `InvokeMethod` client request).

Since there is no concept of a default method provider (all CIM methods
imply actions that are specific to the method). The default provide returns
an exception.

User defined providers may be created for specific CIM classes and namespaces
to override the InvokeMethod in :class:`~pywbem_mock.MethodProvider` with user
methods defined in a subclass of :class:`~pywbem_mock.MethodProvider`.

This module contains the default MethodProvider class which provides the
following:

1. Definition of the provider type (`provider_type = method`).
2. Definition of the API and return for the `InvokeMethod` method required in
   the user-defined subclass

A user-defined method provider is created as follows:

1. Create the subclass of :class:`~pywbem_mock.MethodProvider` with an
   __init__ method, an optional `post_registration_setup` method and the
   `InvokeMethod that will override the same method defined in
   :class:`~pywbem_mock.MethodProvider`.  The input parameters for the
   InvokeMethod will have been already validated in
   :class:`~pywbem_mock.ProviderDispatcher.ProviderDispatcher`.

   The created method should implement any exceptions based on
   :class:`pywbem.CIMError` using the error codes defined in :term:`DSP0200`
   which will be passed back to the client.

   The user-defined class must include the following class variables:

   * `provider_classnames` (:term:`string` or list of :term`string`): defines
     the class(es) that this provider will serve.

   Thus, a user-defined method provider defines a subclass to
   :class:`~pywbem_mock.MethodProvider and defines a `InvokeMethod` method in
   the user-defined subclass to override
   :meth:`~pywbem_mock.MethodProvider.InvokeMethod`.

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
            Defines the repository to be used by request responders.  The
            repository is fully initialized.
        """
        super(MethodProvider, self).__init__(cimrepository)

    ####################################################################
    #
    #   Server responder for InvokeMethod.
    #
    ####################################################################

    def InvokeMethod(self, namespace, MethodName, ObjectName, Params):
        # pylint: disable=invalid-name,no-self-use
        """
        Defines the API and return for a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.InvokeMethod` for both static (ObjectName
        is a class name) and dynamic (ObjectName is a CIMInstanceName) methods

        This method should never be called because there is no concept of a
        default InvokeMethod in WBEM.  All method providers specify specific
        actions.

        This responder calls a function defined by an entry in the methods
        repository. The return from that function is returned to the user.

        Parameters:

          namespace  (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          MethodName (:term:`string`):
            Name of the method to be invoked (case independent).

          ObjectName:
            The object path of the target object, as follows:

            * For instance-level use: The instance path of the target
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `namespace`, and `host` attributes will be ignored.

            * For class-level use: The class path of the target class, as a
              :term:`string`:

              The string is interpreted as a class name in the default
              namespace of the connection (case independent).

          Params (:term:`py:iterable`):
            An iterable of input parameter values for the CIM method. Each item
            in the iterable is a single parameter value and is:

            * :class:`~pywbem.CIMParameter` representing a parameter value. The
              `name`, `value`, `type` and `embedded_object` attributes of this
              object are used.

        Returns:

            A :func:`py:tuple` of (returnvalue, outparams), with these
            tuple items:

            * returnvalue (:term:`CIM data type`):
              Return value of the CIM method.
            * outparams (:term:`py:iterable` of :class:`~pywbem.CIMParameter`):
              Each item represents a single output parameter of the CIM method.
              The :class:`~pywbem.CIMParameter` objects must have at least
              the following properties set:

                * name (:term:`string`): Parameter name (case independent).
                * type (:term:`string`): CIM data type of the parameter.
                * value (:term:`CIM data type`): Parameter value.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_METHOD_NOT_AVAILABLE) because the
              default method is only a placeholder for the API and documentation
              and not a real InvokeMethod action implementation.
        """
        # No default MethodProvider is implemented because all method
        # providers define specific actions in their implementations.
        raise CIMError(CIM_ERR_METHOD_NOT_FOUND)
