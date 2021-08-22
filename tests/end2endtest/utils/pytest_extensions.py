"""
Pytest fixtures for pywbem end2end tests.
"""

from __future__ import absolute_import

import os
import io
import warnings
from contextlib import contextmanager
import json
import subprocess
try:
    from subprocess import DEVNULL
except ImportError:
    # Python 2.7
    from subprocess import PIPE as DEVNULL
import six
import pytest
import yaml

# Note: The wbem_connection fixture uses the es_server fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
# pylint: disable=unused-import
from pytest_easy_server import es_server  # noqa: F401
# pylint: enable=unused-import

from pywbem import WBEMServer, Error, ConnectionError, AuthError, \
    ToleratedServerIssueWarning  # pylint: disable=redefined-builtin

from .utils import latest_profile_inst, ServerObjectCache, \
    WBEMConnectionAsserted, server_func_asserted
from .assertions import assert_association_a1, assert_association_a2, \
    assert_association_a3, assert_association_a4, assert_association_a5, \
    assert_association_a6

# Profile definition file (in end2end directory).
PROFILES_YAML_FILE = os.path.join('tests', 'profiles', 'profiles.yml')

# Profile definition list.
# The list items are profile definition items, as described in the profile
# definition file.
with io.open(PROFILES_YAML_FILE, 'r', encoding='utf-8') as _fp:
    PROFILE_DEFINITION_LIST = yaml.safe_load(_fp)
del _fp  # pylint: disable=undefined-loop-variable


@contextmanager
def server_from_docker(image_name, image_port, host_port, container_name,
                       verbose=False):
    """
    Context manager that creates a started WBEM server from a Docker image
    of a WBEM server, if it does not already exist.

    Upon entry, the context manager checks if a container with that name
    exists. If so, it assumes it contains the server and starts the
    container if not currently started. If a container with the name does not
    exist, the image is pulled from DockerHub (using a local Docker cache)
    and a container with that name is created and started.

    Upon exit, the context manager leaves the container running.

    For simplicity of code, the context manager can also be used when no Docker
    image should be used by specifying image_name=None.

    Note: This function requires the 'docker' command to be available locally.

    Parameters:

      image_name (string):
        Docker image name on DockerHub, e.g. org/name:1.2.3. If None, the
        context manager does nothing and returns None.

      image_port (int): Port number in image

      host_port (int): Port number on host (local) system

      container_name (string): Docker container name to use locally

      verbose (bool): Print messages.

    Returns:
      URL of the running WBEM server, or None if image_name=None.
    """
    if image_name:

        # Find out whether container exists and is running
        try:
            inspect_out = subprocess.check_output(
                ['docker', 'container', 'inspect', container_name],
                stderr=DEVNULL)
        except EnvironmentError as exc:
            raise RuntimeError(
                "Docker does not seem to be installed: {}".format(exc))
        except subprocess.CalledProcessError as exc:
            if exc.returncode > 1:
                raise RuntimeError(
                    "Command 'docker container inspect ...' failed: {}".
                    format(exc))
            container_exists = False
            container_running = False
        else:
            container_exists = True
            if isinstance(inspect_out, six.binary_type):
                inspect_out = inspect_out.decode('utf-8')
            _inspect_dict = json.loads(inspect_out)
            _status = _inspect_dict[0]['State']['Status']
            container_running = (_status == 'running')

        if not container_exists:
            docker_pull_with_cache(image_name, verbose=verbose)
            if verbose:
                print("Creating Docker container {} with "
                      "image {}".format(container_name, image_name))
            subprocess.check_call(
                ['docker', 'create',
                 '--name', container_name,
                 '--publish', '{}:{}'.format(host_port, image_port),
                 image_name],
                stdout=DEVNULL)
        else:
            if verbose:
                print("Using existing Docker container {}".
                      format(container_name))

        if not container_running:
            if verbose:
                print("Starting Docker container {}".format(container_name))
            subprocess.check_call(
                ['docker', 'start', container_name],
                stdout=DEVNULL)
        else:
            if verbose:
                print("Docker container {} was already running".
                      format(container_name))

        yield 'https://localhost:{}'.format(host_port)

        # Leave the container running on exit.
    else:
        yield None


def docker_pull_with_cache(image_name, verbose=False):
    """
    Pull a Docker image from DockerHub, using a Docker cache directory.

    If the cache directory does not exist, it is created.

    If the docker image does not exist in the cache directory, it is
    pulled from DockerHub and saved as a TAR file in the cache directory.

    If the docker image exists as a TAR file in the cache directory, it is
    loaded from the TAR file.

    In any case, the result is that the local Docker has the image available.

    The path name of the cache directory is taken from the env var
    DOCKER_CACHE_DIR and defaults to (see code) if not set.

    Parameters:

      image_name (string): Docker image name on DockerHub, e.g. org/name:1.2.3

      verbose (bool): Print messages.
    """
    cache_dir = os.getenv('DOCKER_CACHE_DIR') or '~/docker-cache'
    cache_dir = os.path.expanduser(cache_dir)

    if not os.path.exists(cache_dir):
        if verbose:
            print("Creating local Docker image cache directory: {}".
                  format(cache_dir))
        os.makedirs(cache_dir, 0o755)

    image_tar_fn = image_name.replace('/', '_').replace(':', '_') + '.tar'
    image_tar_path = os.path.join(cache_dir, image_tar_fn)

    if not os.path.exists(image_tar_path):

        if verbose:
            print("Pulling image from Docker Hub: {}".format(image_name))
        subprocess.check_call(
            ['docker', 'pull', image_name],
            stdout=DEVNULL)

        if verbose:
            print("Saving image {} in local Docker image cache: {}".
                  format(image_name, image_tar_path))
        subprocess.check_call(
            ['docker', 'save', '-o', image_tar_path, image_name],
            stdout=DEVNULL)

    else:

        if verbose:
            print("Loading image {} from local Docker image cache: {}".
                  format(image_name, image_tar_path))
        subprocess.check_call(
            ['docker', 'load', '-i', image_tar_path],
            stdout=DEVNULL)


def skip_if_unsupported_capability(conn, cap_name):
    """
    Skip the pytest testcase if the specified capability is not supported
    by the server at the connection.
    """
    if not supports_capability(conn, cap_name):
        pytest.skip("Server {} does not support capability: {}".
                    format(conn.es_server.nickname, cap_name))


def supports_capability(conn, cap_name):
    """
    Return boolean indicating whether the specified capability is supported
    by the server at the connection.
    """
    supported_caps = conn.es_server.user_defined.get('capabilities', [])
    return cap_name in supported_caps


@pytest.fixture(
    scope='function'
)
def wbem_connection(request, es_server):
    # pylint: disable=redefined-outer-name, unused-argument
    """
    Fixture representing a WBEMConnection object to use for the end2end tests.

    The fixture has function scope, so the connection is created for each
    test function (including their parametrizations).

    The WBEM server defined by the 'es_server' parameter is assumed to exist all
    the time during the test session (= the pytest command). If the server
    has a docker image definition, it is established and torn down
    automatically, but only once during the test session.

    Parameters:
      es_server (easy_server.Server): Pytest fixture resolving to the server to
        be tested against.

    Returns:
      pywbem.WBEMConnection: Connection to the server.
    """

    # Display messages about server that is used
    verbose = False

    # Skip this server if we had a skip reason in an earlier attempt.
    # Note: We add an attribute to the es_server object to store this info.
    skip_msg = getattr(es_server, 'skip_msg', None)
    if skip_msg:
        pytest.skip("Remembered skip reason from earlier attempt: {0}".
                    format(skip_msg))

    nickname = es_server.nickname

    # Keep the usage of the items in the es_server object in sync with the
    # schemas defining them in the es_schema.yml file.

    url = es_server.user_defined['url']
    default_namespace = es_server.user_defined.get('default_namespace', None)
    user = es_server.secrets.get('user', None)
    password = es_server.secrets.get('password', None)
    no_verification = es_server.secrets.get('no_verification', None)
    ca_certs = es_server.secrets.get('ca_certs', None)
    cert_file = es_server.secrets.get('cert_file', None)
    key_file = es_server.secrets.get('key_file', None)
    x509 = dict(cert_file=cert_file, key_file=key_file) \
        if cert_file and key_file else None

    image_port = None
    host_port = None
    container_name = None
    image_name = es_server.user_defined.get('docker_image', None)
    if image_name:
        port_mapping = es_server.user_defined.get('docker_port_mapping', None)
        if port_mapping:
            image_port = int(port_mapping['image'])
            host_port = int(port_mapping['host'])
        container_name = 'pywbem_end2endtest_{}'.format(nickname)

    with server_from_docker(
            image_name, image_port, host_port, container_name,
            verbose=verbose):

        if verbose:
            print("Creating WBEM connection to: {}".format(url))

        conn = WBEMConnectionAsserted(
            url, (user, password), x509=x509,
            ca_certs=ca_certs,
            no_verification=no_verification,
            default_namespace=default_namespace,
            timeout=10,
            es_server=es_server)

        # Check that the server can be reached and authenticated with, by
        # issuing some quick operation. Operation failures are tolerated
        # (e.g. GetQualifier is not supported on SFCB), and the connection and
        # authgentication errors can still be detected because they will be
        # detected before the operation fails.
        try:
            conn.GetQualifier(
                'Association',
                asserted=False)
        except ConnectionError as exc:
            msg = "Server {0} at {1}: Server cannot be reached: {2} - {3}". \
                format(nickname, url, exc.__class__.__name__, exc)
            es_server.skip_msg = msg
            warnings.warn(msg, ToleratedServerIssueWarning)
            pytest.skip(msg)
        except AuthError as exc:
            msg = "Server {0} at {1}: Server cannot be authenticated with: " \
                "{2} - {3}". \
                format(nickname, url, exc.__class__.__name__, exc)
            es_server.skip_msg = msg
            warnings.warn(msg, ToleratedServerIssueWarning)
            pytest.skip(msg)
        except Error:
            # Any other error may be due to the WBEM server not supporting
            # qualifier operations. In that case, we don't optimize.
            es_server.skip_msg = None
        else:
            es_server.skip_msg = None

        yield conn

        if verbose:
            print("Closing WBEM connection to: {}".format(url))
        conn.close()


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

    def init_central_instances(self):
        """
        Initialize the central_inst_paths attribute with the central instances
        of the profile. init_profile() must have been called before.

        The following instance attributes are set:
          * central_inst_paths: central instances as list of CIMInstanceName.
        """

        # init_profile() must have been called before.
        assert getattr(self, 'profile_org', None)
        assert getattr(self, 'profile_name', None)

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
