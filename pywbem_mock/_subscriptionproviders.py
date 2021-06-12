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
This module implements user providerw for the classews required to create and
manage CIM indications subscriptions including: CIM_ListenerDestination,
CIM_IndicationFilter, and CIM_IndicationSubscription.  These providers are
packaged as single file because they are all required together.

This  provider manages creation and deletion of the instances of the
These 3 classes and limits that activity to the server
environment interop namespace.

The user providers extend the basic Create, Modify, Delete functionality by:

1. Adding properties to the instances (ex. PersistenceType as the WBEM
server is expected to do)

2. Complete the key properties of SystemName, etc. which the provider does
not know.

3. Validate that instances are only created in the interop namespace.

4. Validate that reference parameters do exist for CreateInstances and that
They do not exist for DeleteInstances. Ex. You cannot delete a filter that
is included in a subscription.
"""
import six

from nocaselist import NocaseList

from pywbem import CIMError, CIM_ERR_NOT_SUPPORTED, \
    CIM_ERR_INVALID_PARAMETER, CIM_ERR_FAILED, Uint16, CIMDateTime
from pywbem._utils import _format

from ._instancewriteprovider import InstanceWriteProvider
from .config import SYSTEMNAME, SYSTEMCREATIONCLASSNAME

# CIM class name of the classes implemented in these providers
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
LISTENERDESTINATIONS_CLASSNAMES = NocaseList(['CIM_ListenerDestination',
                                              'CIM_ListenerDestinationCIMXML'])


class CommonMethodsMixin(object):
    """
    Common Methods and functionality for the 3 providers defined to support
    indication subscriptions
    """
    def _modify_instance_notsupported(self, modified_instance):
        # pylint: disable=no-self-use
        """
        Generate exception if this method called. Use where Modify
        Instance not permitted
        """
        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            _format("Modification of {0} instances is not allowed: "
                    "{1!A}",
                    modified_instance.classname, modified_instance.path))

    def parameter_is_interop(self, ns, classname):
        # pylint: disable=no-self-use
        """
        Test if the parameter provided in ns is the interop namespace
        """
        if not self.is_interop_namespace(ns):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format(
                    "Cannot create instance of class {0!A} in namespace {1!A}: "
                    "The namespace is not an Interop namespace. "
                    "Valid Interop namespaces are: {2!A}",
                    classname, ns, ", ".join(self.interop_namespace_names)))

    def fix_key_properties(self, new_instance):
        # pylint: disable=no-self-use
        """
        Fix the key properties that are common to many classes (SystemName,
        CreationClassName, SystemCreateionClassName) since these may be
        either not provided with the new instance or incorrect for this
        enviornment
        """
        ccn_pname = 'CreationClassName'
        sys_pname = 'SystemName'
        sccn_pname = 'SystemCreationClassName'

        # Validate  or fix other key values in the new instance
        def _fix_key_prop(pname, test_value, replacement=None):
            if pname not in new_instance or \
                    new_instance[pname].lower != test_value.lower:
                new_instance[pname] = replacement or test_value

        # set the keys to default if they don't exist or have invalid value
        _fix_key_prop(ccn_pname, new_instance.classname,
                      new_instance.classname)
        _fix_key_prop(sys_pname, SYSTEMNAME)
        _fix_key_prop(sccn_pname, SYSTEMCREATIONCLASSNAME)

    def validate_required_properties_exist(self, new_instance, namespace,
                                           required_properties):
        # pylint: disable=no-self-use
        """
        Validate that the properties in required_properties list do exist
        in the new_instance
        """
        for pn in required_properties:
            if pn not in new_instance:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format(
                        "Cannot create instance of class {0!A} in "
                        "namespace {1!A}: "
                        "Missing required property {2!A} in new_instance",
                        new_instance.classname, namespace, pn))

    def validate_no_subscription(self, instance_name):
        """
        Validate that no subscriptions exist containing reference to this
        instance
        """
        # If a subscription exists containing this ListenerDestination,
        # reject delete
        if self.conn.ReferenceNames(instance_name,
                                    ResultClass=SUBSCRIPTION_CLASSNAME):
            # DSP1054 1.2 defines CIM error is raised by the server
            # in that case; we simulate it.
            raise CIMError(
                CIM_ERR_FAILED,
                _format("The instance {} is referenced by "
                        "subscriptions.", instance_name),
                conn_id=self.conn.conn_id)

    def post_register_setup(self, conn):
        """
        Method called by FakedWBEMConnection.register_provider to complete
        initialization of this provider.  This method is called after
        the required classes are installed in the cim_repository

        This is necessary because pywbem_mock does not allow user-defined
        providers for the instance read operations such as EnumerateInstances
        so the instance for each namespace must be exist in the repository.

        This method is common to all of the subscription providers.
        This method:

        1. Validates that the provider classs exist.

        """
        assert self.installed is False

        self.installed = True

        # Validate provider classes installed.  Will generate exception
        # if class does not exist.
        interop_namespace = conn.find_interop_namespace()
        if isinstance(self.provider_classnames, six.string_types):
            clns = [self.provider_classnames]
        else:
            clns = self.provider_classnames
        for cln in clns:
            conn.GetClass(cln, interop_namespace)
        self.conn = conn


class CIMIndicationFilterProvider(CommonMethodsMixin, InstanceWriteProvider):
    # pylint: disable=line-too-long
    """
    Implements the user defined provider for the class CIM_IndicationFilter.

    This provider provides the create, modify, and delete methods for
    adding an instance of the class CIM_Namspace when a namespace is created or
    deleted in a pywbem mock environment.

    This class and the instances of this class only exist in the WBEM server
    Interop namespace per DMTF definitions.

    This class __init__ saves the  cimrepository variable used by methods in
    this class and by methods of its superclasses (i.e.  InstanceWriteProvider).

    the provider defines the class level attribute `provider_classnames`
    (cim_indicationfilter)

    This provider presumes that an Interop namespace has been created before
    the provider object is constructed and fails the constructor if
    there is not interop_namespace
    """  # noqa: E501
    # pylint: enable=line-too-long

    # This class level attribute must exist to define the CIM classname(es) .
    # for which this provider is responsible.
    #: provider_classnames (:term:`string` or list of :term:`string`):
    #:        The classname for this provider
    provider_classnames = FILTER_CLASSNAME

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the CIM repository to be used by the provider.
        """
        super(CIMIndicationFilterProvider, self).__init__(cimrepository)

        # Tried to make this common but that failed because it could not
        # find the init_common method.
        # self.init_common(FILTER_CLASSNAME)

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create indication filter provider (for class "
                        "{0}): "
                        "No Interop namespace exists in the CIM repository. "
                        "Valid Interop namespaces are: {1}",
                        FILTER_CLASSNAME,
                        ", ".join(self.interop_namespace_names)))

        self.installed = False  # test if provider previously installed.
        self.conn = None

    def __repr__(self):
        return _format(
            "CIMIndicationFilterProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, new_instance):
        """
        Create an instance of the CIM_IndicationFilter class in an Interop
        namespace of the CIM repository, and if not yet existing create the new
        namespace in the CIM repository.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        Parameters:

          namespace (:term:`string`):
            Must be a valid Interop namespace.

          new_instance (:class:`~pywbem.CIMInstance`):
            The following applies regarding its properties:
            * 'Name' property: This property is required since it defines the
              name of the new namespace to be created.
            * 'CreationClassName' property: This property is required and its
              value must match the class name of the new instance.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER) if namespace
            is not the Interop namespace in the CIM repository or the Name
            property does not exist or the other properties cannot be added to
            the instance.
        """
        self.parameter_is_interop(namespace, new_instance.classname)

        required_properties = ['Name']

        self.validate_required_properties_exist(new_instance, namespace,
                                                required_properties)
        # validates and possibly modifies the key properties except Name
        self.fix_key_properties(new_instance)

        # Add missing properties that the might come from CIM_IndicationService
        # Issue # 2719, Should the following be set by the server or client
        new_instance['IndividualSubscriptionSupported'] = True

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMIndicationFilterProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        """
        Modification of CIM_IndicationFilter instance not allowed
        """
        self._modify_instance_notsupported(modified_instance)

    def DeleteInstance(self, InstanceName):
        """
        Delete an instance of the CIM_IndicationFilter class in an Interop
        namespace of the CIM repository unless it has an outstanding
        association through a subscription.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        The namespace to be deleted must be empty and must not be the Interop
        namespace.

        Parameters:

          InstanceName: (:class:`~pywbem.CIMInstanceName`):
            The keybinding `Name` must exist; it defines the namespace to be
            deleted.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY)
        """

        # The provider dispatcher ensures that provider methods are only called
        # for the registered classes.
        # And this provider sets only a single class, not a list.
        assert InstanceName.classname.lower() == \
            CIMIndicationFilterProvider.provider_classnames.lower()

        self.validate_no_subscription(InstanceName)

        # Delete the instance from the CIM repository
        instance_store = self.cimrepository.get_instance_store(
            InstanceName.namespace)
        instance_store.delete(InstanceName)


class CIMListenerDestinationProvider(CommonMethodsMixin, InstanceWriteProvider):
    # pylint: disable=line-too-long
    """
    Implements the user defined provider for the class
    CIM_ListenerDestination.

    This provider provides the create, modify, and delete methods for adding an
    instance of the class CIM_ListenerDestination when a namespace is
    created or deleted in a pywbem mock environment.

    This class and the instances of this class only exist in the WBEM server
    Interop namespace per DMTF definitions.

    This class __init__ saves the  cimrepository variable used by methods in
    this class and by methods of its superclasses (i.e.  InstanceWriteProvider).

    The provider defines the class level attribute `provider_classnames`
    (CIM_ListenerDestination)

    This provider presumes that an Interop namespace has been created before
    the provider object is constructed and fails the constructor if
    there is not interop_namespace
    """  # noqa: E501
    # pylint: enable=line-too-long

    # This class level attribute must exist to define the CIM classname(es) .
    # for which this provider is responsible.
    #: provider_classnames (:term:`string`):
    #:        The classnames for this provider
    provider_classnames = LISTENERDESTINATIONS_CLASSNAMES

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the CIM repository to be used by the provider.
        """
        super(CIMListenerDestinationProvider, self).__init__(cimrepository)

        # self.init_common(LISTENERDESTINATIONS_CLASSNAMES)

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create indication filter provider (for classes "
                        "({0}): "
                        "No Interop namespace exists in the CIM repository. "
                        "Valid Interop namespaces are: {1}",
                        ", ".join(LISTENERDESTINATIONS_CLASSNAMES),
                        ", ".join(self.interop_namespace_names)))

        self.installed = False  # test if provider previously installed.
        self.conn = None

    def __repr__(self):
        return _format(
            "CIMListenerDestinationProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, new_instance):
        """
        Create an instance of the CIM_ListenerDestination class in an
        Interop namespace of the CIM repository, and if not yet existing create
        the new namespace in the CIM repository.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        Parameters:

          namespace (:term:`string`):
            Must be a valid Interop namespace.

          new_instance (:class:`~pywbem.CIMInstance`):
            The following applies regarding its properties:
            * 'Name' property: This property is required since it defines the
              name of the new namespace to be created.
            * 'CreationClassName' property: This property is required and its
              value must match the class name of the new instance.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER) if namespace
            is not the Interop namespace in the CIM repository or the Name
            property does not exist or the other properties cannot be added to
            the instance.
        """
        self.parameter_is_interop(namespace, new_instance.classname)

        ccn_pname = 'CreationClassName'
        name_pname = 'Name'
        sys_pname = 'SystemName'
        sccn_pname = 'SystemCreationClassName'

        # Validate that required properties are specified in the new instance
        self.validate_required_properties_exist(new_instance, namespace,
                                                [name_pname])

        # Validate  or fix other key values in the new instance
        def _fix_key_prop(pname, new_prop_value, replacement=None):
            if pname not in new_instance or \
                    new_instance[pname].lower != new_prop_value.lower():
                new_instance[pname] = replacement or new_prop_value

        # Set the keys to default if they don't exist or have invalid value
        _fix_key_prop(ccn_pname, new_instance.classname,
                      new_instance.classname)
        _fix_key_prop(sys_pname, SYSTEMNAME)
        _fix_key_prop(sccn_pname, SYSTEMCREATIONCLASSNAME)

        # Add missing properties that the might come from CIM_IndicationService

        # ISSUE #2712: should we do PersistenceType in pywbem from the
        # client since this parameter determines the level of persistence
        # of the object? If it is not set, the server sets it to 2(permanent).

        new_instance['Protocol'] = Uint16(2)
        if 'PersistenceType' not in new_instance:
            new_instance['PersistenceType'] = Uint16(2)

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMListenerDestinationProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        """
        Modification of CIM_ListenerDestination instance not allowed
        """
        self._modify_instance_notsupported(modified_instance)

    def DeleteInstance(self, InstanceName):
        """
        Delete an instance of the CIM_ListenerDestination class in an
        Interop namespace of the CIM repository unless it has an outstanding
        association through a subscription.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        The namespace to be deleted must be empty and must not be the Interop
        namespace.

        Parameters:

          InstanceName: (:class:`~pywbem.CIMInstanceName`):
            The keybinding `Name` must exist; it defines the namespace to be
            deleted.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY)
        """

        # The provider dispatcher ensures that provider methods are only called
        # for the registered classes.
        # And this provider sets a list of classes as provider classes
        assert InstanceName.classname in \
            CIMListenerDestinationProvider.provider_classnames

        self.validate_no_subscription(InstanceName)

        # Delete the instance from the CIM repository
        instance_store = self.cimrepository.get_instance_store(
            InstanceName.namespace)
        instance_store.delete(InstanceName)


class CIMIndicationSubscriptionProvider(CommonMethodsMixin,
                                        InstanceWriteProvider):
    # pylint: disable=line-too-long
    """
    Implements the user defined provider for the class CIM_IndicationFilter.

    This provider provides the create, modify, and delete methods for
    adding an instance of the class CIM_Namspace when a namespace is created or
    deleted in a pywbem mock environment.

    This class and the instances of this class only exist in the WBEM server
    Interop namespace per DMTF definitions.

    This class __init__ saves the  cimrepository variable used by methods in
    this class and by methods of its superclasses (i.e.  InstanceWriteProvider).

    The provider defines the class level attribute `provider_classnames`
    (CIM_indicationsubscription)

    This provider assures that an Interop namespace has been created before
    the provider object is constructed and fails the constructor if
    there is not interop_namespace
    """  # noqa: E501
    # pylint: enable=line-too-long

    # This class level attribute must exist to define the CIM classname(es) .
    # for which this provider is responsible.
    #: provider_classnames (:term:`string`):
    #:        The classname for this provider
    provider_classnames = SUBSCRIPTION_CLASSNAME

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the CIM repository to be used by the provider.
        """
        super(CIMIndicationSubscriptionProvider, self).__init__(cimrepository)
        # self.init_common(FILTER_CLASSNAME)

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create indication filter provider (for class "
                        "{0}): "
                        "No Interop namespace exists in the CIM repository. "
                        "Valid Interop namespaces are: {1}",
                        FILTER_CLASSNAME,
                        ", ".join(self.interop_namespace_names)))

        self.installed = False  # test if provider previously installed.
        self.conn = None

    def __repr__(self):
        return _format(
            "CIMIndicationFilterProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, new_instance):
        """
        Create an instance of the CIM_IndicationFilter class in an Interop
        namespace of the CIM repository, and if not yet existing create the new
        namespace in the CIM repository.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        Parameters:

          namespace (:term:`string`):
            Must be a valid Interop namespace.

          new_instance (:class:`~pywbem.CIMInstance`):
            The following applies regarding its properties:
            * 'Name' property: This property is required since it defines the
              name of the new namespace to be created.
            * 'CreationClassName' property: This property is required and its
              value must match the class name of the new instance.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER) if namespace
            is not the Interop namespace in the CIM repository or the Name
            property does not exist or the other properties cannot be added to
            the instance.
        """
        self.parameter_is_interop(namespace, new_instance.classname)

        required_properties = ["Filter", "Handler"]

        # Validate that required properties are specified in the new instance

        self.validate_required_properties_exist(new_instance, namespace,
                                                required_properties)

        # Add missing properties that the might come from CIM_IndicationService

        new_instance['SubscriptionStartTime'] = CIMDateTime.now()
        new_instance['TimeOfLastStateChange'] = CIMDateTime.now()
        new_instance['OnFatalErrorPolicy'] = Uint16(2)
        new_instance['RepeatNotificationPolicy'] = Uint16(2)
        new_instance['SubscriptionState'] = Uint16(2)

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMIndicationSubscriptionProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        """
        Modification of CIM_IndicationSubscription instance not allowed
        """
        self._modify_instance_notsupported(modified_instance)

    def DeleteInstance(self, InstanceName):
        """
        Delete an instance of the CIM_IndicationSubscription class in an Interop
        namespace of the CIM repository unless it has an outstanding
        association through a subscription.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        The namespace to be deleted must be empty and must not be the Interop
        namespace.

        Parameters:

          InstanceName: (:class:`~pywbem.CIMInstanceName`):
            The keybinding `Name` must exist; it defines the namespace to be
            deleted.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY)
        """

        # The provider dispatcher ensures that provider methods are only called
        # for the registered classes.
        # And this provider sets only a single class, not a list.
        assert InstanceName.classname.lower() == \
            CIMIndicationSubscriptionProvider.provider_classnames.lower()

        # Delete the instance from the CIM repository
        instance_store = self.cimrepository.get_instance_store(
            InstanceName.namespace)
        instance_store.delete(InstanceName)
