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
This module implements user providerw for the classes required to create and
manage CIM indications subscriptions including: CIM_ListenerDestinationCIMXML,
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

from pywbem import CIMError, CIM_ERR_NOT_SUPPORTED, \
    CIM_ERR_INVALID_PARAMETER, CIM_ERR_FAILED, Uint16, CIMDateTime, \
    CIMProperty
from pywbem._utils import _format

from ._instancewriteprovider import InstanceWriteProvider
from .config import SYSTEMNAME, SYSTEMCREATIONCLASSNAME

# CIM class name of the classes implemented in these providers
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
LISTENERDESTINATION_CLASSNAME = 'CIM_ListenerDestinationCIMXML'


def set_property(instance, name, value, conditional=True):
    """
    Add a new property and value to instance or modify value if property
    exists. If conditional is True, only add if property does not exist.
    Otherwise, always set new value into property.
    """
    if conditional:
        if name not in instance:
            instance[name] = value
    else:
        instance[name] = value


class CommonMethodsMixin(object):
    """
    Common Methods and functionality for the 3 providers defined to support
    indication subscriptions
    """

    def validate_modify_instance(self, modified_instance,
                                 modifiable_properties=None,
                                 IncludeQualifiers=None):
        # pylint: disable=invalid-name
        """
        Common code for ModifyInstance method for subscription providers.

        This code validates that the modify instance is allowed and validates
        that the properties to be modified are the ones allowed in the
        modified_instance.

        This method assumes that:

        - The provider method is called only for the registered class and
          namespace (only applies to user-defined providers).

        - The Python types of all input parameters to this provider method are
          as specified below.

        - The classnames in modified_instance are consistent between
          instance and instance path.

        - The namespace exists in the CIM repository.

        - The creation class of the instance to be modified exists in the
          namespace of the CIM repository.

        - The instance to be modified exists in the namespace of the CIM
          repository.

        - All properties in modified_instance that are to be modified are
          exposed (i.e. defined and inherited with any overrides resolved) by
          the creation class in the CIM repository, and have the same
          type-related attributes (i.e. type, is_array, embedded_object).

        - No key properties are requested to change their values.

        Validation that should be performed by this provider method:

        - modified_instance does not specify any changed values for
          properties that are not allowed to be changed by the client,
          depending on the model implemented by the provider.

        Parameters:
          modified_instance (:class:`~pywbem.CIMInstance`):
            A representation of the modified CIM instance, also indicating its
            instance path, with exactly the set of properties to be modified.

            This object is a deep copy of the original client parameter, and may
            be modified by the provider as needed, before storing it in the
            CIM repository.

            The `path` attribute of this object will be set and is the
            instance path of the instance to be modified in the CIM repository.
            Its `namespace`, `classname` and `keybindings` attributes
            will be set. The names will be in any lexical case.

            The `classname` attribute of this object will specify the creation
            class of the instance to be modified, in any lexical case.

            The `properties` attribute of this object will specify exactly the
            set of properties that are to be updated, taking into account the
            original ModifiedInstance and PropertyList input parameters of the
            ModifyInstance() client call.
            The lexical case of the property names has been adjusted to match
            the lexical cae of the property definitions in the creation class
            in the CIM repository.

            The `qualifiers` attribute of this object, if non-empty, should
            be ignored by the provider, because instance-level qualifiers have
            been deprecated in CIM.

          modifiable_properties (:term:`string` or list of :term:`string`):
            Property names of properties that are modifiable by. If
            properties that are not modifiable are included, the request
            is rejected with CIM_ERR_INVALID_PARAMETER

        Raises:
            CIMError exception if either the modification not allowed
            (supported_properties is None) or the properties in the modified
            instance are not included in the modifiable_properties list
        """

        if not modifiable_properties:
            raise CIMError(
                CIM_ERR_NOT_SUPPORTED,
                _format("Modification of {0} instances is not allowed: "
                        "{1!A}",
                        modified_instance.classname, modified_instance.path))
        inst_properties = modified_instance.keys()

        invalid_props = [pname for pname in inst_properties if pname not in
                         modifiable_properties]

        if IncludeQualifiers:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Modification of qualifiers is for {0}"
                        "not allowed.", modified_instance.classname))
        if invalid_props:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Modification of properties {0} instance of {1!A} is "
                        "not allowed: {2!A}", ", ".join(invalid_props),
                        modified_instance.classname, modified_instance.path))

        if modified_instance.classname != SUBSCRIPTION_CLASSNAME:
            self.validate_no_subscription(modified_instance.path)

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
        CreationClassName, SystemCreationClassName) since these may be
        either not provided, None, or incorrect value for this environment with
        the new instance, they may be overridden. This works only for
        the filter and destination classes that contain the same set of
        key properties.
        """
        ccn_pname = 'CreationClassName'
        sys_pname = 'SystemName'
        sccn_pname = 'SystemCreationClassName'

        # Validate  or fix other key values in the new instance
        def _fix_key_prop(pname, test_value, replacement=None):
            """
            Replace property pname with either replacement if replacement not
            None or test_value if property does not exist, is None, or not same
            value as test_value
            """
            if pname not in new_instance or new_instance[pname] is None or \
                    new_instance[pname].lower != test_value.lower:
                new_instance[pname] = replacement or test_value

        # Set the keys to default if they don't exist  are None,  or have
        # invalid value
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
        instance.

        Parameters:

          instance_name (:class:`~pywbem.CIMInstanceName`)
            Instance name of the target instance. The class must be either
            the filter class or the listener destination class

        Returns:
          Returns if there are no corresponding subscriptions.
        """
        # If a subscription exists containing this ListenerDestination,
        # reject delete
        if self.conn.ReferenceNames(instance_name,
                                    ResultClass=SUBSCRIPTION_CLASSNAME):
            # DSP1054 1.2 defines CIM error is raised by the server
            # in that case; we simulate it.
            raise CIMError(
                CIM_ERR_FAILED,
                _format("The instance {0} is referenced by "
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

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create indication filter provider for class: "
                        "{0}. "
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
        # pylint: disable=invalid-name
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
        # Validates and possibly modifies the key properties except Name
        self.fix_key_properties(new_instance)

        # Note: No test for SourceNamespace valid namespaces because profile
        # allows creating filters for not-yet-created namespaces

        # Add missing properties that the might come from CIM_IndicationService
        # Issue # 2719, Should the following be set by the server or client
        set_property(new_instance, 'IndividualSubscriptionSupported', True)

        set_property(new_instance, 'SourceNamespace',
                     CIMProperty('SourceNamespace', None, type='string'))

        set_property(new_instance, 'Description',
                     "Pywbem mock CIMIndicationFilterProvider instance")

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMIndicationFilterProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        # pylint: disable=invalid-name
        """
        Modification of CIM_IndicationFilter instance allowed for selected
        properties. See the documentation in
        CommonMethodsMixin.validate_modify_instance for parameter
        documentation.
        """
        modifiable_properties = ['IndividualSubscriptionSupported']

        self.validate_modify_instance(
            modified_instance,
            modifiable_properties=modifiable_properties,
            IncludeQualifiers=IncludeQualifiers)

        return super(CIMIndicationFilterProvider, self).ModifyInstance(
            modified_instance, IncludeQualifiers=IncludeQualifiers)

    def DeleteInstance(self, InstanceName):  # pylint: disable=invalid-name
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
    CIM_ListenerDestinationCIMXML.

    This provider provides the create, modify, and delete methods for adding an
    instance of the class CIM_ListenerDestinationCIMXML when a namespace is
    created or deleted in a pywbem mock environment.

    This class and the instances of this class only exist in the WBEM server
    Interop namespace per DMTF definitions.

    This class __init__ saves the  cimrepository variable used by methods in
    this class and by methods of its superclasses (i.e.  InstanceWriteProvider).

    The provider defines the class level attribute `provider_classnames`
    (CIM_ListenerDestinationCIMXML)

    This provider presumes that an Interop namespace has been created before
    the provider object is constructed and fails the constructor if
    there is not interop_namespace
    """  # noqa: E501
    # pylint: enable=line-too-long

    # This class level attribute must exist to define the CIM classname(es) .
    # for which this provider is responsible.
    #: provider_classnames (:term:`string`):
    #:        The classnames for this provider
    provider_classnames = LISTENERDESTINATION_CLASSNAME

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the CIM repository to be used by the provider.
        """
        super(CIMListenerDestinationProvider, self).__init__(cimrepository)

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create listener destination provider for "
                        "classes: ({0}). "
                        "No Interop namespace exists in the CIM repository. "
                        "Valid Interop namespaces are: {1}",
                        ", ".join(LISTENERDESTINATION_CLASSNAME),
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
        # pylint: disable=invalid-name
        """
        Create an instance of the CIM_ListenerDestinationCIMXML class in an
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

        required_properties = [name_pname]

        # Validate that required properties are specified in the new instance
        self.validate_required_properties_exist(new_instance, namespace,
                                                required_properties)

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
        # if not already in instance
        set_property(new_instance, 'Protocol', Uint16(2))

        set_property(new_instance, 'PersistenceType', Uint16(2))

        set_property(new_instance, 'Description',
                     "pywbem mock CIMListenerDestinationProvider instance")

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMListenerDestinationProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        # pylint: disable=invalid-name
        """
        Modification of CIM_ListenerDestinationXIMXML instance allowed only for
        selected properties. See the documentation in
        CommonMethodsMixin.validate_modify_instance for parameter documentation.
        """
        modifiable_properties = []

        self.validate_modify_instance(
            modified_instance,
            modifiable_properties=modifiable_properties,
            IncludeQualifiers=IncludeQualifiers)

        return super(CIMListenerDestinationProvider, self).ModifyInstance(
            modified_instance, IncludeQualifiers=IncludeQualifiers)

    def DeleteInstance(self, InstanceName):  # pylint: disable=invalid-name
        """
        Delete an instance of the CIM_ListenerDestinationCIMXML class in an
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

        return super(CIMListenerDestinationProvider, self).DeleteInstance(
            InstanceName)


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

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create indication subscription provider for "
                        "class: {0}. "
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
        # pylint: disable=invalid-name
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
            * The 'Filter' and 'Handler' reference properties must exist.

            * If 'SubscriptionDuration' exists, 'SubscriptionTimeRemaining'
              will be set.
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

        self.validate_required_properties_exist(new_instance, namespace,
                                                required_properties)

        # Add missing properties that the might come from CIM_IndicationService

        new_instance['SubscriptionStartTime'] = CIMDateTime.now()
        new_instance['TimeOfLastStateChange'] = CIMDateTime.now()

        # Conditionally add the following properties
        set_property(new_instance, 'OnFatalErrorPolicy', Uint16(2))

        set_property(new_instance, 'RepeatNotificationPolicy', Uint16(2))

        set_property(new_instance, 'SubscriptionState', Uint16(2))

        if 'SubscriptionDuration' in new_instance:
            new_instance['SubscriptionTimeRemaining'] = \
                new_instance['SubscriptionDuration']
        else:
            new_instance['SubscriptionDuration'] = CIMProperty(
                'SubscriptionDuration', None, type='uint64')

        set_property(new_instance, 'SubscriptionInfo',
                     CIMProperty('SubscriptionInfo', None, type='string'))

        set_property(new_instance, 'Description',
                     "Pywbem mock CIMIndicationSubscriptionProvider instance")

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMIndicationSubscriptionProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        # pylint: disable=invalid-name
        """
        Modification of CIM_IndicationSubscription instance allowed only for
        selected properties. See the documentation in
        CommonMethodsMixin.validate_modify_instance for parameter documentation.
        """
        # NOTE: The choice of modifiable properties is just to support tests
        #       and may not reflect user needs since profile definition is
        #       flexible
        modifiable_properties = ['SubscriptionInfo', 'SubscriptionState',
                                 'SubscriptionDuration']

        # Validates the modify instance  but does not change any properties.
        # If not valid, it generates exception
        self.validate_modify_instance(
            modified_instance, modifiable_properties=modifiable_properties,
            IncludeQualifiers=IncludeQualifiers)

        if modified_instance['SubscriptionDuration']:
            modified_instance['SubscriptionTimeRemaining'] = \
                modified_instance['SubscriptionDuration']

        if modified_instance['SubscriptionDuration']:
            modified_instance['SubscriptionTimeRemaining'] = \
                modified_instance['SubscriptionDuration']

        modified_instance['TimeOfLastStateChange'] = CIMDateTime.now()

        return super(CIMIndicationSubscriptionProvider, self).ModifyInstance(
            modified_instance, IncludeQualifiers=IncludeQualifiers)

    def DeleteInstance(self, InstanceName):  # pylint: disable=invalid-name
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

        return super(CIMIndicationSubscriptionProvider, self).DeleteInstance(
            InstanceName)
