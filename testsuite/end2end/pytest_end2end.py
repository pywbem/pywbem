"""
pytest support for pywbem end2end tests.
"""

from __future__ import absolute_import

import os
import pytest

from pywbem import WBEMConnection
from server_file import ServerDefinitionFile, ServerDefinition

__all__ = ['server_definition', 'default_namespace', 'wbem_connection']

# Server nickname or server group nickname in WBEM server definition file
TESTSERVER = os.getenv('TESTSERVER', 'default')
SD_LIST = list(ServerDefinitionFile().iter_servers(TESTSERVER))


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
