#!/usr/bin/env python

"""
End2end tests for interop namespace.
"""

from __future__ import absolute_import, print_function

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
from pytest_end2end import wbem_connection, default_namespace, server_definition  # noqa: F401, E501

from pywbem import WBEMServer


def test_interop_in_namespaces(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Determine interop namespace, determine all namespaces, and verify that
    the interop namespace is in all namespaces.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)

    interop_ns = server.interop_ns
    namespaces = server.namespaces

    assert interop_ns in namespaces, \
        "for server at URL {1!r}".format(wbem_connection.url)
