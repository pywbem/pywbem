"""
pytest support for pywbem end2end tests.
"""

from __future__ import absolute_import

import os
import warnings
import pytest
import yaml
import six

from pywbem import WBEMConnection, WBEMServer, CIMInstance, CIMInstanceName, \
    ConnectionError, AuthError, Error
from server_file import ServerDefinitionFile, ServerDefinition
from _utils import _latest_profile_inst, path_equal, path_in, instance_of

__all__ = ['server_definition', 'default_namespace', 'wbem_connection',
           'profile_definition', 'single_profile_definition', 'ProfileTest']

# Server nickname or server group nickname in WBEM server definition file
TESTSERVER = os.getenv('TESTSERVER', 'default')
SD_LIST = list(ServerDefinitionFile().iter_servers(TESTSERVER))

PROFILES_YAML_FILE = 'profiles.yml'
with open(PROFILES_YAML_FILE, 'r') as fp:
    PROFILE_DEFINITIONS = yaml.load(fp)


def fixtureid_server_definition(fixture_value):
    """
    Return a fixture ID to be used by py.test, for fixture
    `server_definition()`.

    Parameters:
      * fixture_value (ServerDefinition): The server definition of the
        WBEM server the test runs against.
    """
    sd = fixture_value
    assert isinstance(sd, ServerDefinition)
    return "server_definition={}".format(sd.nickname)


@pytest.fixture(
    params=SD_LIST,
    scope='module',
    ids=fixtureid_server_definition
)
def server_definition(request):
    """
    Fixture representing the set of WBEM server definitions to use for the
    end2end tests.

    Returns the `ServerDefinition` object of each server to test against.
    """
    return request.param


@pytest.fixture(
    scope='module'
)
def wbem_connection(request, server_definition):
    """
    Fixture representing the set of WBEMConnection objects to use for the
    end2end tests.

    Returns the `WBEMConnection` object of each server to test against.
    """
    sd = server_definition

    x509 = dict(cert_file=sd.cert_file, key_file=sd.key_file) \
        if sd.cert_file and sd.key_file else None

    conn = WBEMConnection(
        sd.url, (sd.user, sd.password),
        x509=x509,
        ca_certs=sd.ca_certs,
        no_verification=sd.no_verification,
        timeout=10)

    # Check that the server can be reached and authenticated with, by issuing
    # some quick operation. Operation failures are tolerated (e.g. GetQualifier
    # is not supported on SFCB), and the connection and authgentication errors
    # can still be detected because they will be detected before the operation
    # fails.
    try:
        conn.GetQualifier('Association')
    except ConnectionError as exc:
        msg = "Test server at {0!r} cannot be reached. {1}: {2}". \
            format(sd.url, exc.__class__.__name__, exc)
        warnings.warn(msg, RuntimeWarning)
        pytest.skip(msg)
    except AuthError as exc:
        msg = "Test server at {0!r} cannot be authenticated with. {1}: {2}". \
            format(sd.url, exc.__class__.__name__, exc)
        warnings.warn(msg, RuntimeWarning)
        pytest.skip(msg)
    except Error:
        pass

    return conn


def fixtureid_default_namespace(fixture_value):
    """
    Return a fixture ID to be used by py.test, for fixture
    `default_namespace()`.

    Parameters:
      * fixture_value (string): The default namespace for the test.
    """
    ns = fixture_value
    return "default_namespace={}".format(ns)


@pytest.fixture(
    params=[None, 'root/cimv2', 'interop', 'root/interop'],
    scope='module',
    ids=fixtureid_default_namespace
)
def default_namespace(request):
    """
    Fixture representing the set of default namespaces to open connections
    with.

    Returns the default namespace as a string.
    """
    return request.param


def fixtureid_profile_definition(fixture_value):
    """
    Return a fixture ID to be used by py.test, for fixture
    `profile_definition()`.

    Parameters:
      * fixture_value (dict): The profile definition dictionary of the profile.
    """
    pd = fixture_value
    assert isinstance(pd, dict)
    assert 'registered_name' in pd
    assert 'registered_org' in pd
    return "profile_definition={0}:{1}". \
        format(pd['registered_org'], pd['registered_name'])


def _apply_profile_definition_defaults(pd):
    if 'reference_direction' not in pd:
        pd['reference_direction'] = None
    if pd['reference_direction'] is None:
        org = pd['registered_org']
        if org == 'SNIA':
            pd['reference_direction'] = 'snia'
        elif org == 'DMTF':
            pd['reference_direction'] = 'dmtf'
        else:
            raise ValueError(
                "The reference_direction item of a profile definition can "
                "only be defaulted when the registered organisation is DMTF "
                "or SNIA, but it is {0}".format(org))
    if 'scoping_class' not in pd:
        pd['scoping_class'] = None
    if 'scoping_path' not in pd:
        pd['scoping_path'] = None
    return pd


def single_profile_definition(org, name):
    """
    Return a single profile definition dictionary for the specified org and
    name. If a profile definition does not exist, returns None.

    Optional items in the profile definition dictionary are generated with
    their default values.
    """
    assert org is not None
    assert name is not None
    for pd in PROFILE_DEFINITIONS:
        if pd['registered_org'] == org and pd['registered_name'] == name:
            pd = _apply_profile_definition_defaults(pd.copy())
            return pd
    return None


@pytest.fixture(
    params=PROFILE_DEFINITIONS,
    scope='module',
    ids=fixtureid_profile_definition
)
def profile_definition(request):
    """
    Fixture representing the set of profile definitions to use for the
    end2end tests.

    Returns the profile definition dictionary of each profile to test against.
    For dict items, see the description in profiles.yaml.

    Optional items in the dictionary are generated with their default values.
    """
    pd = _apply_profile_definition_defaults(request.param.copy())
    return pd


class ProfileTest(object):
    """
    Base class for end2end tests on a specific profile.
    """

    def init_profile(self, conn, profile_org, profile_name):
        """
        Initialize attributes for the profile.

        The input parameters are simply stored as attributes.
        In addition, the following attributes are set:
        * server: WBEMServer object created from the connection.
        * assert_msg: Message to be used for assertions, to provide context.
        * profile_inst: CIMInstance for the CIM_RegisteredProfile object for
          the profile. If it does not exist, the testcase is skipped.
        * profile_definition: Profile definition dictionary for the profile.
        """
        # pylint: disable=attribute-defined-outside-init
        self.conn = conn
        self.profile_org = profile_org
        self.profile_name = profile_name

        self.server = WBEMServer(self.conn)
        profile_insts = self.server.get_selected_profiles(
            self.profile_org, self.profile_name)
        if not profile_insts:
            pytest.skip("{0} {1} profile is not advertised on server {2!r}".
                        format(self.profile_org, self.profile_name,
                               self.conn.url))
        self.profile_inst = _latest_profile_inst(profile_insts)

        self.profile_definition = single_profile_definition(
            self.profile_org, self.profile_name)
        assert self.profile_definition is not None
        # pylint: enable=attribute-defined-outside-init

    def assert_instance_of(self, path_list, classname):
        """
        Assert that a set of CIM instances (identified by its instance paths)
        is of a particular CIM class, i.e. that the creation class of the CIM
        instances or one of its superclasses has the specified class name.

        Because there are WBEM servers without support for class operations,
        this is implemented without relying on class operations. The function
        performs an EnumerateInstanceNames operation on the desired class in
        the namespace of the instance in question, and verifies that the
        instance in question is in the result.

        Parameters:

            path_list (CIMInstanceName or CIMInstance or tuple/list
              thereof): The CIM instance paths. The instance paths must have a
              namespace and classname set. The namespace must be the same
              across all instance paths. The host portion of the instance
              paths is treated specially when comparing them, as described
              in path_equal().

            classname (string): The CIM class name.
        """

        # Parameters are checked and transformed in instance_of()

        # TODO 2018-12 AM: Improve performance by avoiding EI on each path
        if not isinstance(path_list, (tuple, list)):
            path_list = [path_list]
        for path in path_list:
            if not instance_of(self.conn, path, classname):
                raise AssertionError(
                    "Instance at {0!r} is not of class {1!r}".
                    format(path.to_wbem_uri(), classname))

    def assert_instance_consistency(self, instance, path):
        """
        Assert that an instance and an instance path are consistent:

        - They must have the same classname.
        - The instance must have the key properties matching the keybindings
          of the instance path.

        The 'path' attribute of the instance is ignored for this purpose.
        Of course, this function can be used to verify consistency of
        an instance and its 'path' attribute by passing it as the 'path'
        parameter.

        Parameters:

            instance (CIMInstance): The CIM instance to be verified.

            path (CIMInstanceName): The CIM instance path to be verified.
        """

        # Check parameters
        assert isinstance(instance, CIMInstance)
        assert isinstance(path, CIMInstanceName)

        if instance.classname.lower() != path.classname.lower():
            raise AssertionError(
                "Inconsistent instance and instance path: Instance classname "
                "{0!r} does not match classname of instance path {1!r}".
                format(instance.classname, path.to_wbem_uri()))

        for key_name in path.keybindings:

            if key_name not in instance.properties:
                raise AssertionError(
                    "Inconsistent instance and instance path: Instance does"
                    "not have key property {0!r} of instance path {1!r}".
                    format(key_name, path.to_wbem_uri()))

            if instance.properties[key_name].value != \
                    path.keybindings[key_name]:
                raise AssertionError(
                    "Inconsistent instance and instance path: For key {0!r}, "
                    "instance property value {1!r} does not match instance "
                    "path keybinding value {2!r}".
                    format(key_name, instance.properties[key_name],
                           path.keybindings[key_name]))

    def assert_mandatory_properties(self, instance, property_list):
        """
        Assert that an instance has non-null values for a set of properties.

        Parameters:

            instance (CIMInstance): The CIM instance to be verified.

            property_list (iterable of string): The property names.
        """

        # Check parameters
        assert isinstance(instance, CIMInstance)

        instance_prop_names = instance.properties.keys()
        for prop_name in property_list:
            assert isinstance(prop_name, six.string_types)

            if prop_name not in instance_prop_names:
                raise AssertionError(
                    "Mandatory properties issue: Instance of class {0!r} does "
                    "not have mandatory property {1!r}".
                    format(instance.classname, prop_name))

            prop_value = instance.properties[prop_name]
            if prop_value is None:
                raise AssertionError(
                    "Mandatory properties issue: Instance of class {0!r} has "
                    "mandatory property {1!r} but with a value of NULL".
                    format(instance.classname, prop_name))

    def assert_property_one_of(self, instance, prop_name, value_list):
        """
        Assert that a simple (= non-array) CIM property of an instance has a
        value that is one of a set of allowable values.

        Parameters:

            instance (CIMInstance): The CIM instance that has the property to
              be verified.

            prop_name (string): Name of the CIM property to be verified.

            value_list (iterable of values): The set of allowable values for
              the property.
        """

        # Check parameters
        assert isinstance(instance, CIMInstance)
        assert isinstance(prop_name, six.string_types)
        prop = instance.properties[prop_name]
        assert not prop.is_array

        prop_value = prop.value
        if prop_value not in value_list:
            raise AssertionError(
                "Property value issue: The value of simple property {0!r} in "
                "an instance of class {1!r} is not in the allowable set of "
                "values {2!r}, but is {3!r}".
                format(prop_name, instance.classname, value_list, prop_value))

    def assert_property_contains(self, instance, prop_name, value):
        """
        Assert that a CIM array property (of an instance) contains a particular
        value.

        Parameters:

            instance (CIMInstance): The CIM instance that has the property to
              be verified.

            prop_name (string): Name of the CIM property to be verified.

            value (value): The value.
        """

        # Check parameters
        assert isinstance(instance, CIMInstance)
        assert isinstance(prop_name, six.string_types)
        prop = instance.properties[prop_name]
        assert prop.is_array

        prop_values = prop.value
        if value not in prop_values:
            raise AssertionError(
                "Property value issue: The value of array property {0!r} in "
                "an instance of class {1!r} does not contain value {2!r}, "
                "but is {3!r}".
                format(prop_name, instance.classname, value, prop_values))

    def assert_path_equal(self, path1, path1_msg, path2, path2_msg):
        """
        Assert that two instance paths are equal, with special treatment
        of their host component:
        - The host component is compared literally (but case insensitively),
          i.e. no IP address to hostname translation is performed.
        - If one or both of the instance paths have their host component set to
          None, the comparison is considered equal.

        For keys of the instance paths that are references, the special
        treatment of their host component is applied recursively.
        """

        # Check parameters; rest is checked in path_equal()
        assert isinstance(path1_msg, six.string_types)
        assert isinstance(path2_msg, six.string_types)

        if not path_equal(path1, path2):
            raise AssertionError(
                "Instance path issue: Instance path {0!r} ({1}) "
                "does not match instance path {2!r} ({3})".
                format(path1.to_wbem_uri(), path1_msg,
                       path2.to_wbem_uri(), path2_msg))

    def assert_path_in(self, path, path_msg, path_list, path_list_msg):
        """
        Assert that an instance path is in a list of instance paths or
        instances, with special treatment of their host component as described
        in assert_path_equal().
        """

        # Check parameters; rest is checked in path_in()
        assert isinstance(path_msg, six.string_types)
        assert isinstance(path_list_msg, six.string_types)

        if not path_in(path, path_list):
            raise AssertionError(
                "Instance path issue: Instance path {0!r} ({1}) "
                "is not in expected set of instance paths ({2})".
                format(path.to_wbem_uri(), path_msg, path_list_msg))

    def _assert_association_consistency(
            self,
            source_path, source_role,
            assoc_insts, assoc_insts_msg, assoc_paths, assoc_paths_msg,
            assoc_class,
            far_insts, far_insts_msg, far_paths, far_paths_msg,
            far_class, far_role):

        assert len(far_insts) == len(far_paths), \
            "Number of far end instances {0} ({1}) does not match " \
            "number of far end paths {2} ({3})". \
            format(len(far_insts), far_insts_msg, len(far_paths),
                   far_paths_msg)
        assert len(assoc_insts) == len(assoc_paths), \
            "Number of association instances {0} ({1}) does not match " \
            "number of association paths {2} ({3})". \
            format(len(assoc_insts), assoc_insts_msg, len(assoc_paths),
                   assoc_paths_msg)
        assert len(far_insts) == len(assoc_insts), \
            "Number of far end instances {0} ({1}) does not match " \
            "number of association instances {2} ({3})". \
            format(len(far_insts), far_insts_msg, len(assoc_insts),
                   assoc_insts_msg)

        self.assert_instance_of(far_insts, far_class)
        for inst in far_insts:
            self.assert_instance_consistency(inst, inst.path)
        for path in far_paths:
            self.assert_path_in(
                path, far_paths_msg,
                far_insts, "path of {0}".format(far_insts_msg))

        self.assert_instance_of(assoc_insts, assoc_class)
        for inst in assoc_insts:
            self.assert_instance_consistency(inst, inst.path)
            assert source_role in inst.path.keybindings
            self.assert_path_equal(
                inst.path.keybindings[source_role],
                "source end {0!r} of {1}".format(source_role, assoc_insts_msg),
                source_path,
                "source instance")
            assert far_role in inst.path.keybindings
            self.assert_path_in(
                inst.path.keybindings[far_role],
                "far end {0!r} of {1}".format(far_role, assoc_insts_msg),
                far_paths,
                far_paths_msg)
        for path in assoc_paths:
            self.assert_path_in(
                path, assoc_paths_msg,
                assoc_insts, "path of {0}".format(assoc_insts_msg))

    def assert_association(self, source_path, source_role, assoc_class,
                           far_role, far_class):
        """
        Assert that navigation from a source instance across an association
        succeeds.

        This test performs a number of different approaches for determining the
        associated and association instances and their instance paths.

        Consistency is verified within each approach and across the
        approaches.

        Returns:
            tuple of:
            - list of associated (far end) instances
            - list of association instances
        """

        # Approach a1:
        # - associations: References with manual far end filtering
        # - far end: Associators with operation-based far end filtering
        a1_assoc_insts = self.conn.References(
            source_path,
            ResultClass=assoc_class,
            Role=source_role)
        a1_assoc_insts = [
            inst for inst in a1_assoc_insts
            if far_role in inst.path.keybindings and
            instance_of(self.conn, inst.path.keybindings[far_role], far_class)
        ]
        a1_assoc_paths = [inst.path for inst in a1_assoc_insts]
        a1_far_insts = self.conn.Associators(
            source_path,
            AssocClass=assoc_class,
            ResultClass=far_class,
            Role=source_role,
            ResultRole=far_role)
        a1_far_paths = [inst.path for inst in a1_far_insts]
        self._assert_association_consistency(
            source_path, source_role,
            a1_assoc_insts,
            "manually filtered result of References (a1)",
            a1_assoc_paths,
            "paths of manually filtered result of References (a1)",
            assoc_class,
            a1_far_insts,
            "result of Associators (a1)",
            a1_far_paths,
            "paths of result of Associators (a1)",
            far_class, far_role)

        # Approach a2:
        # - associations: References with manual far end filtering
        # - far end: Associators with manual far end filtering
        a2_assoc_insts = self.conn.References(
            source_path,
            ResultClass=assoc_class,
            Role=source_role)
        a2_assoc_insts = [
            inst for inst in a2_assoc_insts
            if far_role in inst.path.keybindings and
            instance_of(self.conn, inst.path.keybindings[far_role], far_class)
        ]
        a2_assoc_paths = [inst.path for inst in a2_assoc_insts]
        a2_assoc_far_paths = [path.keybindings[far_role]
                              for path in a2_assoc_paths]
        a2_far_insts = self.conn.Associators(
            source_path,
            AssocClass=assoc_class,
            Role=source_role)
        a2_far_insts = [
            inst for inst in a2_far_insts
            if path_in(inst.path, a2_assoc_far_paths) and
            instance_of(self.conn, inst.path, far_class)
        ]
        a2_far_paths = [inst.path for inst in a2_far_insts]
        self._assert_association_consistency(
            source_path, source_role,
            a2_assoc_insts,
            "manually filtered result of References (a2)",
            a2_assoc_paths,
            "paths of manually filtered result of References (a2)",
            assoc_class,
            a2_far_insts,
            "manually filtered result of Associators (a2)",
            a2_far_paths,
            "paths of manually filtered result of Associators (a2)",
            far_class, far_role)

        # Check consistency with approach a1
        assert len(a2_assoc_paths) == len(a1_assoc_paths)
        for path in a2_assoc_paths:
            self.assert_path_in(
                path,
                "path of manually filtered result of References (a2)",
                a1_assoc_paths,
                "path of manually filtered result of References (a1)")
        assert len(a2_far_paths) == len(a1_far_paths)
        for path in a2_far_paths:
            self.assert_path_in(
                path,
                "path of manually filtered result of Associators (a2)",
                a1_far_paths,
                "path of result of Associators (a1)")

        # Approach a3:
        # - associations: ReferenceNames with manual far end filtering and
        #   GetInstance.
        # - far end: AssociatorNames with operation-based far end filtering and
        #   GetInstance.
        a3_assoc_paths = self.conn.ReferenceNames(
            source_path,
            ResultClass=assoc_class,
            Role=source_role)
        a3_assoc_paths = [
            path for path in a3_assoc_paths
            if far_role in path.keybindings and
            instance_of(self.conn, path.keybindings[far_role], far_class)
        ]
        a3_assoc_insts = []
        for path in a3_assoc_paths:
            _inst = self.conn.GetInstance(path)
            a3_assoc_insts.append(_inst)
        a3_far_paths = self.conn.AssociatorNames(
            source_path,
            AssocClass=assoc_class,
            ResultClass=far_class,
            Role=source_role,
            ResultRole=far_role)
        a3_far_insts = []
        for path in a3_far_paths:
            _inst = self.conn.GetInstance(path)
            a3_far_insts.append(_inst)
        self._assert_association_consistency(
            source_path, source_role,
            a3_assoc_insts,
            "GetInstance on manually filtered result of ReferenceNames (a3)",
            a3_assoc_paths,
            "manually filtered result of ReferenceNames (a3)",
            assoc_class,
            a3_far_insts,
            "GetInstance on result of AssociatorNames (a3)",
            a3_far_paths,
            "result of AssociatorNames (a3)",
            far_class, far_role)

        # Check consistency with approach a1
        assert len(a3_assoc_paths) == len(a1_assoc_paths)
        for path in a3_assoc_paths:
            self.assert_path_in(
                path,
                "manually filtered result of ReferenceNames (a3)",
                a1_assoc_paths,
                "path of manually filtered result of References (a1)")
        assert len(a3_far_paths) == len(a1_far_paths)
        for path in a3_far_paths:
            self.assert_path_in(
                path,
                "result of AssociatorNames (a3)",
                a1_far_paths,
                "path of result of Associators (a1)")

        # Approach a4:
        # - associations: ReferenceNames with manual far end filtering and
        #   GetInstance.
        # - far end: AssociatorNames with manual far end filtering and
        #   GetInstance.
        a4_assoc_paths = self.conn.ReferenceNames(
            source_path,
            ResultClass=assoc_class,
            Role=source_role)
        a4_assoc_paths = [
            path for path in a4_assoc_paths
            if far_role in path.keybindings and
            instance_of(self.conn, path.keybindings[far_role], far_class)
        ]
        a4_assoc_far_paths = [path.keybindings[far_role]
                              for path in a4_assoc_paths]
        a4_assoc_insts = []
        for path in a4_assoc_paths:
            _inst = self.conn.GetInstance(path)
            a4_assoc_insts.append(_inst)
        a4_far_paths = self.conn.AssociatorNames(
            source_path,
            AssocClass=assoc_class,
            Role=source_role)
        a4_far_paths = [
            path for path in a4_far_paths
            if path_in(path, a4_assoc_far_paths) and
            instance_of(self.conn, path, far_class)
        ]
        a4_far_insts = []
        for path in a4_far_paths:
            _inst = self.conn.GetInstance(path)
            a4_far_insts.append(_inst)
        self._assert_association_consistency(
            source_path, source_role,
            a4_assoc_insts,
            "GetInstance on manually filtered result of ReferenceNames (a4)",
            a4_assoc_paths,
            "manually filtered result of ReferenceNames (a4)",
            assoc_class,
            a4_far_insts,
            "GetInstance on manually filtered result of AssociatorNames (a4)",
            a4_far_paths,
            "manually filtered result of AssociatorNames (a4)",
            far_class, far_role)

        # Check consistency with approach a1
        assert len(a4_assoc_paths) == len(a1_assoc_paths)
        for path in a4_assoc_paths:
            self.assert_path_in(
                path,
                "manually filtered result of ReferenceNames (a4)",
                a1_assoc_paths,
                "path of manually filtered result of References (a1)")
        assert len(a4_far_paths) == len(a1_far_paths)
        for path in a4_far_paths:
            self.assert_path_in(
                path,
                "manually filtered result of AssociatorNames (a4)",
                a1_far_paths,
                "path of result of Associators (a1)")

        # Approach a5:
        # - associations: EnumerateInstances of the association and manual
        #   filtering.
        # - far end: GetInstance on the far end keys of the associations.
        a5_assoc_insts = self.conn.EnumerateInstances(
            namespace=source_path.namespace,
            ClassName=assoc_class)
        a5_assoc_insts = [
            inst for inst in a5_assoc_insts
            if source_role in inst.path.keybindings and
            path_equal(inst.path.keybindings[source_role], source_path) and
            far_role in inst.path.keybindings and
            instance_of(self.conn, inst.path.keybindings[far_role], far_class)
        ]
        a5_assoc_paths = [inst.path for inst in a5_assoc_insts]
        a5_assoc_far_paths = [path.keybindings[far_role]
                              for path in a5_assoc_paths]
        a5_far_insts = []
        for path in a5_assoc_far_paths:
            _inst = self.conn.GetInstance(path)
            a5_far_insts.append(_inst)
        a5_far_paths = [inst.path for inst in a5_far_insts]
        self._assert_association_consistency(
            source_path, source_role,
            a5_assoc_insts,
            "manually filtered result of "
            "EnumerateInstances on association class (a5)",
            a5_assoc_paths,
            "paths of manually filtered result of "
            "EnumerateInstances on association class (a5)",
            assoc_class,
            a5_far_insts,
            "GetInstance on far ends of manually filtered result of "
            "EnumerateInstances on association class (a5)",
            a5_far_paths,
            "far ends of manually filtered result of "
            "EnumerateInstances on association class (a5)",
            far_class, far_role)

        # Check consistency with approach a1
        assert len(a5_assoc_paths) == len(a1_assoc_paths)
        for path in a5_assoc_paths:
            self.assert_path_in(
                path,
                "path of manually filtered result of EnumerateInstances on "
                "association class (a5)",
                a1_assoc_paths,
                "path of manually filtered result of References (a1)")
        assert len(a5_far_paths) == len(a1_far_paths)
        for path in a5_far_paths:
            self.assert_path_in(
                path,
                "far ends of manually filtered result of EnumerateInstances "
                "on association class (a5)",
                a1_far_paths,
                "path of result of Associators (a1)")

        # Approach a6:
        # - associations: EnumerateInstanceNames of the association and manual
        #   filtering, followed by GetInstance.
        # - far end: GetInstance on the far end keys of the associations.
        a6_assoc_paths = self.conn.EnumerateInstanceNames(
            namespace=source_path.namespace,
            ClassName=assoc_class)
        a6_assoc_paths = [
            path for path in a6_assoc_paths
            if source_role in path.keybindings and
            path_equal(path.keybindings[source_role], source_path) and
            far_role in path.keybindings and
            instance_of(self.conn, path.keybindings[far_role], far_class)
        ]
        a6_assoc_far_paths = [path.keybindings[far_role]
                              for path in a6_assoc_paths]
        a6_assoc_insts = []
        for path in a6_assoc_paths:
            _inst = self.conn.GetInstance(path)
            a6_assoc_insts.append(_inst)
        a6_far_insts = []
        for path in a6_assoc_far_paths:
            _inst = self.conn.GetInstance(path)
            a6_far_insts.append(_inst)
        a6_far_paths = [inst.path for inst in a6_far_insts]
        self._assert_association_consistency(
            source_path, source_role,
            a6_assoc_insts,
            "GetInstance on manually filtered result of "
            "EnumerateInstanceNames on association class (a6)",
            a6_assoc_paths,
            "manually filtered result of "
            "EnumerateInstanceNames on association class (a6)",
            assoc_class,
            a6_far_insts,
            "GetInstance on far ends of manually filtered result of "
            "EnumerateInstanceNames on association class (a6)",
            a6_far_paths,
            "far ends of manually filtered result of "
            "EnumerateInstanceNames on association class (a6)",
            far_class, far_role)

        # Check consistency with approach a1
        assert len(a6_assoc_paths) == len(a1_assoc_paths)
        for path in a6_assoc_paths:
            self.assert_path_in(
                path,
                "manually filtered result of EnumerateInstanceNames on "
                "association class (a6)",
                a1_assoc_paths,
                "path of manually filtered result of References (a1)")
        assert len(a6_far_paths) == len(a1_far_paths)
        for path in a6_far_paths:
            self.assert_path_in(
                path,
                "far ends of manually filtered result of "
                "EnumerateInstanceNames on association class (a6)",
                a1_far_paths,
                "path of result of Associators (a1)")

        return a1_far_insts, a1_assoc_insts
