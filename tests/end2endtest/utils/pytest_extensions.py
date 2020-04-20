"""
Pytest fixtures for pywbem end2end tests.
"""

from __future__ import absolute_import

import os
import warnings
import pytest
import yaml

from pywbem import WBEMServer, Error, ConnectionError, AuthError, \
    ToleratedServerIssueWarning

from .server_definition_file import ServerDefinition, \
    ServerDefinitionFile
from .utils import latest_profile_inst, ServerObjectCache, \
    WBEMConnectionAsserted, server_func_asserted
from .assertions import assert_association_a1, assert_association_a2, \
    assert_association_a3, assert_association_a4, assert_association_a5, \
    assert_association_a6

# Server nickname or server group nickname in WBEM server definition file
TESTSERVER = os.getenv('TESTSERVER', 'default')
SD_LIST = ServerDefinitionFile().list_servers(TESTSERVER)

# Profile definition file (in end2end directory).
PROFILES_YAML_FILE = os.path.join('tests', 'profiles', 'profiles.yml')

# Profile definition list.
# The list items are profile definition items, as described in the profile
# definition file.
with open(PROFILES_YAML_FILE, 'r') as _fp:
    PROFILE_DEFINITION_LIST = yaml.load(_fp)
del _fp  # pylint: disable=undefined-loop-variable


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
    return "server_definition={0}".format(sd.nickname)


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
    # pylint: disable=redefined-outer-name, unused-argument
    """
    Fixture representing the set of WBEMConnection objects to use for the
    end2end tests.  This fixture uses the
    implementation_namespace item from the server_definition as the
    default namespace if that item exists in the server_definition.

    Returns the `WBEMConnection` object of each server to test against.
    """
    sd = server_definition  # ServerDefinition object

    # Skip this server if we had a skip reason in an earlier attempt
    skip_msg = getattr(sd, 'skip_msg', None)
    if skip_msg:
        pytest.skip("Remembered skip reason from earlier attempt: {0}".
                    format(skip_msg))

    x509 = dict(cert_file=sd.cert_file, key_file=sd.key_file) \
        if sd.cert_file and sd.key_file else None

    # Define the WBEMConnection default_namespace as the
    # implementation_namespace if that data exists, else define it as
    # None which invokes root/cimv2 as the default namespace.
    # NOTE: Since WBEMConnection assigns root/cimv2 as default, there is
    # no way to really know if a valid implementation namespace was defined.
    conn = WBEMConnectionAsserted(
        sd.url, (sd.user, sd.password),
        x509=x509,
        ca_certs=sd.ca_certs,
        no_verification=sd.no_verification,
        default_namespace=sd.implementation_namespace,
        timeout=10,
        server_definition=sd)

    # Check that the server can be reached and authenticated with, by issuing
    # some quick operation. Operation failures are tolerated (e.g. GetQualifier
    # is not supported on SFCB), and the connection and authgentication errors
    # can still be detected because they will be detected before the operation
    # fails.
    try:
        conn.GetQualifier(
            'Association',
            asserted=False)
    except ConnectionError as exc:
        msg = "Server {0} at {1}: Server cannot be reached: {2} - {3}". \
            format(sd.nickname, sd.url, exc.__class__.__name__, exc)
        sd.skip_msg = msg
        warnings.warn(msg, ToleratedServerIssueWarning)
        pytest.skip(msg)
    except AuthError as exc:
        msg = "Server {0} at {1}: Server cannot be authenticated with: " \
            "{2} - {3}". \
            format(sd.nickname, sd.url, exc.__class__.__name__, exc)
        sd.skip_msg = msg
        warnings.warn(msg, ToleratedServerIssueWarning)
        pytest.skip(msg)
    except Error:
        # Any other error may be due to the WBEM server not supporting
        # qualifier operations. In that case, we don't optimize.
        sd.skip_msg = None
    else:
        sd.skip_msg = None

    return conn


def fixtureid_default_namespace(fixture_value):
    """
    Return a fixture ID to be used by py.test, for fixture
    `default_namespace()`.

    Parameters:
      * fixture_value (string): The default namespace for the test.
    """
    ns = fixture_value
    return "default_namespace={0}".format(ns)


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
    return "profile_definition={0}:{1}:{2}". \
        format(pd['registered_org'], pd['registered_name'],
               pd.get('registered_version', 'any'))


def _apply_profile_definition_defaults(pd):
    """Set the profile definition defaults"""
    if 'reference_direction' not in pd:
        pd['reference_direction'] = None
    if 'registered_version' not in pd:
        pd['registered_version'] = None
    if pd['reference_direction'] is None:
        org = pd['registered_org']
        if org == 'SNIA':
            pd['reference_direction'] = 'snia'
        elif org == 'DMTF':
            pd['reference_direction'] = 'dmtf'
        else:
            raise ValueError(
                "Profile definition error: The reference_direction item of a "
                "profile definition can only be defaulted when the registered "
                "organisation is DMTF or SNIA, but it is {0}".format(org))
    if 'scoping_class' not in pd:
        pd['scoping_class'] = None
    if 'scoping_path' not in pd:
        pd['scoping_path'] = None
    return pd


def single_profile_definition(org, name, version=None):
    """
    Return a single profile definition dictionary for the specified org and
    name, and optionally version. If version is None, it matches the
    profile definition with the latest version. Profile definitions that do
    not specify a version always match.
    Optional items in the profile definition dictionary are generated with
    their default values.

    If a profile definition does not exist, returns None.
    """
    assert org is not None
    assert name is not None

    # Determine profile definitions with the specified org and name
    pd_list = []
    for pd in PROFILE_DEFINITION_LIST:
        if org != pd['registered_org'] or name != pd['registered_name']:
            continue
        pd_list.append(pd)

    # Determine profile definition with the specified version or latest
    if version:
        # Search profile definition with that version or without a version
        version_info = version.split('.')
        for pd in pd_list:
            pd_version = pd.get('registered_version', None)
            if not pd_version:
                # A profile definition without a version always matches
                return _apply_profile_definition_defaults(pd.copy())
            pd_version_info = pd_version.split('.')
            if pd_version_info == version_info:
                return _apply_profile_definition_defaults(pd.copy())
    else:
        # Search profile definition with latest version or without a version
        latest_pd_version_info = (-1, -1, -1)
        latest_pd = None
        for pd in pd_list:
            pd_version = pd.get('registered_version', None)
            if not pd_version:
                # A profile definition without a version always matches
                return _apply_profile_definition_defaults(pd.copy())
            pd_version_info = pd_version.split('.')
            if pd_version_info > latest_pd_version_info:
                latest_pd_version_info = pd_version_info
                latest_pd = pd
        if latest_pd:
            return _apply_profile_definition_defaults(latest_pd.copy())

    # No such profile definition exists
    return None


@pytest.fixture(
    params=PROFILE_DEFINITION_LIST,
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


@pytest.fixture(
    params=[
        # the function for a1 must be first, because its results are stored
        # in the object cache for use by the subsequent functions.
        assert_association_a1,
        assert_association_a2,
        assert_association_a3,
        assert_association_a4,
        assert_association_a5,
        assert_association_a6,
    ],
    scope='module',
)
def assert_association_func(request):
    """
    Fixture representing a function for asserting association traversal.

    Returns the function.

    Interface of the function:

        Parameters:
          conn, profile_id, source_path, source_role, assoc_class, far_role,
          far_class

        Returns:
            tuple of:
            - list of associated (far end) instances
            - list of association instances
    """
    return request.param


class ProfileTest(object):
    """
    Base class for end2end tests on a specific profile.
    """

    object_cache = ServerObjectCache()

    def init_profile(self, conn, profile_org, profile_name,
                     profile_version=None):
        """
        Initialize attributes for the profile.

        The following instance attributes are set:
          * conn: conn argument (WBEMConnection).
          * profile_org: profile_org argument (registered org string).
          * profile_name: profile_name argument (registered name string).
          * profile_version: profile_version argument (registered version
            string), may be None.
          * server: WBEMServer object created from the connection.
          * profile_definition: Profile definition dictionary for the profile.
          * profile_id: org:name:version string to identify the profile.
            The version defaults to 'any' if profile_version is None.
          * profile_inst: CIMInstance for the CIM_RegisteredProfile object for
            the profile. If it does not exist, the testcase is skipped.
        """
        # pylint: disable=attribute-defined-outside-init
        assert conn is not None
        assert profile_org is not None
        assert profile_name is not None
        self.conn = conn
        self.profile_org = profile_org
        self.profile_name = profile_name
        self.profile_version = profile_version  # May be None

        self.server = WBEMServer(conn)
        self.profile_definition = single_profile_definition(
            self.profile_org, self.profile_name, self.profile_version)
        assert self.profile_definition is not None

        self.profile_id = "{0}:{1}:{2}".format(
            self.profile_org, self.profile_name, self.profile_version or 'any')
        profile_insts_id = self.profile_id + ':profile_insts'

        try:
            profile_insts = self.object_cache.get_list(
                conn.url, profile_insts_id)
        except KeyError:
            profile_insts = server_func_asserted(
                self.server, 'get_selected_profiles',
                registered_org=self.profile_org,
                registered_name=self.profile_name,
                registered_version=self.profile_version)
            self.object_cache.add_list(
                conn.url, profile_insts_id, profile_insts)

        if not profile_insts:
            pytest.skip("{0} {1} profile (version {2}) is not advertised "
                        "on server {3!r}".
                        format(self.profile_org, self.profile_name,
                               self.profile_version or 'any', self.conn.url))

        self.profile_inst = latest_profile_inst(profile_insts)
        # pylint: enable=attribute-defined-outside-init

    def init_central_instances(self, conn):
        """
        Initialize attributes for the profile by calling init_profile()
        and get the central instances.

        The following instance attributes are set, in addition to
        init_profile():
          * central_inst_paths: central instances as list of CIMInstanceName.
        """

        self.init_profile(conn)
        # TODO: Add profile_org and profile_name arguments

        central_paths_id = self.profile_id + ':central_paths'

        try:
            central_paths = self.object_cache.get_list(
                self.conn.url, central_paths_id)
        except KeyError:
            central_paths = server_func_asserted(
                self.server, 'get_central_instances',
                profile_path=self.profile_inst.path,
                central_class=self.profile_definition['central_class'],
                scoping_class=self.profile_definition['scoping_class'],
                scoping_path=self.profile_definition['scoping_path'],
                reference_direction=self.profile_definition[
                    'reference_direction'])
            self.object_cache.add_list(
                self.conn.url, central_paths_id, central_paths)

        # pylint: disable=attribute-defined-outside-init
        self.central_inst_paths = central_paths
