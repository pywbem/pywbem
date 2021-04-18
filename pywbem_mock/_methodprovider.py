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
The :class:`~pywbem_mock.MethodProvider` class provides the default
implementation of the ``InvokeMethod`` provider method by means of
:meth:`~pywbem_mock.MethodProvider.InvokeMethod`.

The default implementation raises CIMError with CIM_ERR_METHOD_NOT_AVAILABLE,
because there is no meaningful default implementation of CIM methods.
A user-defined method provider implements this provider method. The method
description linked above provides a detailed definition of the input parameters,
return values, and required behavior.

The following example implements method ``Method1`` defined in class
``CIM_Foo_sub_sub`` that is defined as follows:

.. code-block:: text

        [Description ("Subclass of CIM_Foo_sub")]
    class CIM_Foo_sub_sub : CIM_Foo_sub {

        string cimfoo_sub_sub;

            [Description("Sample method with input and output parameters")]
        uint32 Method1(
            [IN ( false), OUT, Description("Response param 2")]
          string OutputParam2);
    };

The example implementation of method ``Method1`` in the user-defined method
provider modifies the value of property ``cimfoo_sub_sub`` of the instance,
and returns it as its output parameter ``OutputParam2``:

.. code-block:: python

    from pywbem import CIMInstanceName, CIMError, \\
        CIM_ERR_INVALID_PARAMETER, CIM_ERR_METHOD_NOT_AVAILABLE
    from pywbem_mock import MethodProvider

    class MyMethodProvider(MethodProvider):

        provider_classnames = 'CIM_Foo_sub_sub'

        def InvokeMethod(self, methodname, localobject, params):

            if methodname.lower() == 'method1':
                if isinstance(localobject, CIMClassName):
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        "CIM method {0} must be invoked on a CIM instance".
                        format(methodname))
                return self.Method1(localobject, params)
            else:
                raise CIMError(CIM_ERR_METHOD_NOT_AVAILABLE)

        def Method1(self, localobject, params):
            '''
            Implementation of CIM method 'Method1'.
            '''
            namespace = localobject.namespace
            instance_store = self.cimrepository.get_instance_store(namespace)

            # Get the instance the method was invoked on, from the CIM
            # repository (as a copy)
            instance = instance_store.get(localobject.path)  # a copy

            # Modify a property value in the local copy of the instance
            if 'cimfoo_sub_sub' not in instance.properties:
                instance.properties['cimfoo_sub_sub'] = 'new'
            instance.properties['cimfoo_sub_sub'] += '+'

            # Update the instance in the CIM repository from the changed
            # local instance
            instance_store.update(localobject.path, instance)

            # Return the property value in the output parameter
            outputparam2 = instance.properties['cimfoo_sub_sub']
            out_params = [
                CIMParameter('OutputParam2', type='string', value=outputparam2),
            ]

            # Set the return value of the CIM method
            return_value = 0

            return (return_value, out_params)
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

    *New in pywbem 1.0 as experimental and finalized in 1.2.*

    User method providers are defined by creating a subclass of this class and
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
            Defines the repository to be used by the provider.
        """
        super(MethodProvider, self).__init__(cimrepository)

    def InvokeMethod(self, methodname, localobject, params):
        # pylint: disable=invalid-name,no-self-use
        # pylint: disable=line-too-long
        """
        Default provider method for
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

            * out_params (:class:`~py3:colletions.abc.Sequence` or :class:`~py3:colletions.abc.Mapping`):
              Output parameters of the method invocation.

              If ``Sequence``, the items must be :class:`~pywbem.CIMParameter`
              in any order, with these attributes set:

                * name (:term:`string`): Parameter name
                * value (:term:`CIM data type`): Parameter value

              If ``Mapping``, the items must be as follows:

                * key (:term:`string`): Parameter name
                * value (:term:`CIM data type` or :class:`~pywbem.CIMParameter`): Parameter value

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
