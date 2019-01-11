"""
Pytest fixtures for pywbem end2end tests.
"""

from __future__ import absolute_import

import os
import warnings
import pytest
import yaml

from pywbem import WBEMConnection, WBEMServer, ConnectionError, AuthError, \
    Error, ToleratedServerIssueWarning
from server_file import ServerDefinitionFile, ServerDefinition
from _utils import latest_profile_inst, ServerObjectCache
from assertions import assert_association_a1, assert_association_a2, \
    assert_association_a3, assert_association_a4, assert_association_a5, \
    assert_association_a6

# Server nickname or server group nickname in WBEM server definition file
TESTSERVER = os.getenv('TESTSERVER', 'default')
SD_LIST = list(ServerDefinitionFile().iter_servers(TESTSERVER))

# Profile definition file (in end2end directory).
PROFILES_YAML_FILE = 'profiles.yml'

# Profile definition list.
# The list items are profile definition items, as described in the profile
# definition file.
with open(PROFILES_YAML_FILE, 'r') as _fp:
    PROFILE_DEFINITION_LIST = yaml.load(_fp)
del _fp

# Profile definition dictionary.
# The dict key is 'org:name', for optimized direct access.
# the dict values are profile definition items, as described in the profile
# definition file.
PROFILE_DEFINITION_DICT = dict()
for _pd in PROFILE_DEFINITION_LIST:
    _key = '{0}:{1}'.format(_pd['registered_org'],
                            _pd['registered_name'])
    PROFILE_DEFINITION_DICT[_key] = _pd
del _pd, _key


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

    # Skip this server if we had a skip reason in an earlier attempt
    skip_msg = getattr(sd, 'skip_msg', None)
    if skip_msg:
        pytest.skip("Remembered skip reason from earlier attempt: {0}".
                    format(skip_msg))

    x509 = dict(cert_file=sd.cert_file, key_file=sd.key_file) \
        if sd.cert_file and sd.key_file else None

    conn = WBEMConnection(
        sd.url, (sd.user, sd.password),
        x509=x509,
        ca_certs=sd.ca_certs,
        no_verification=sd.no_verification,
        timeout=10)

    conn.server_definition = sd

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
        sd.skip_msg = msg
        warnings.warn(msg, ToleratedServerIssueWarning)
        pytest.skip(msg)
    except AuthError as exc:
        msg = "Test server at {0!r} cannot be authenticated with. {1}: {2}". \
            format(sd.url, exc.__class__.__name__, exc)
        sd.skip_msg = msg
        warnings.warn(msg, ToleratedServerIssueWarning)
        pytest.skip(msg)
    except Error:
        sd.skip_msg = None
    finally:
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
                "Profile definition error: The reference_direction item of a "
                "profile definition can only be defaulted when the registered "
                "organisation is DMTF or SNIA, but it is {0}".format(org))
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
    pd_key = "{0}:{1}".format(org, name)
    try:
        pd = PROFILE_DEFINITION_DICT[pd_key]
    except KeyError:
        return None
    pd = _apply_profile_definition_defaults(pd.copy())
    return pd


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

    def init_profile(self, conn, profile_org, profile_name):
        """
        Initialize attributes for the profile.

        The following instance attributes are set:
          * conn: conn argument (WBEMConnection).
          * profile_org: profile_org argument (registered org string).
          * profile_name: profile_name argument (registered name string).
          * server: WBEMServer object created from the connection.
          * profile_definition: Profile definition dictionary for the profile.
          * profile_id: org:name string to identify the profile
          * profile_inst: CIMInstance for the CIM_RegisteredProfile object for
            the profile. If it does not exist, the testcase is skipped.
        """
        # pylint: disable=attribute-defined-outside-init
        self.conn = conn
        self.profile_org = profile_org
        self.profile_name = profile_name

        self.server = WBEMServer(conn)
        self.profile_definition = single_profile_definition(
            profile_org, profile_name)
        assert self.profile_definition is not None

        self.profile_id = "{0}:{1}".format(profile_org, profile_name)
        profile_insts_id = self.profile_id + ':profile_insts'

        try:
            profile_insts = self.object_cache.get_list(
                conn.url, profile_insts_id)
        except KeyError:
            profile_insts = self.server.get_selected_profiles(
                profile_org, profile_name)
            self.object_cache.add_list(
                conn.url, profile_insts_id, profile_insts)

        if not profile_insts:
            pytest.skip("{0} {1} profile is not advertised on server "
                        "{2!r}".
                        format(profile_org, profile_name, self.conn.url))

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

        central_paths_id = self.profile_id + ':central_paths'

        try:
            central_paths = self.object_cache.get_list(
                self.conn.url, central_paths_id)
        except KeyError:
            central_paths = self.server.get_central_instances(
                self.profile_inst.path,
                central_class=self.profile_definition['central_class'],
                scoping_class=self.profile_definition['scoping_class'],
                scoping_path=self.profile_definition['scoping_path'],
                reference_direction=self.profile_definition[
                    'reference_direction'])
            self.object_cache.add_list(
                self.conn.url, central_paths_id, central_paths)

        self.central_inst_paths = central_paths
