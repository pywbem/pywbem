#!/usr/bin/env python

import sys

from pywbem import WBEMConnection
from pywbem.server import WBEMServer, ValueMapping

def explore_server(server_url, username, password):

    print("WBEM server URL:\n  %s" % server_url)

    conn = WBEMConnection(server_url, (username, password))
    server = WBEMServer(conn)

    print("Brand:\n  %s" % server.brand)
    print("Version:\n  %s" % server.version)
    print("Interop namespace:\n  %s" % server.interop_ns)

    print("All namespaces:")
    for ns in server.namespaces:
        print("  %s" % ns)

    print("Advertised management profiles:")
    org_vm = ValueMapping.for_property(server, server.interop_ns,
        'CIM_RegisteredProfile', 'RegisteredOrganization')
    for inst in server.profiles:
        print("  %s %s Profile %s" % \
            (org_vm.tovalues(str(inst['RegisteredOrganization'])),
             inst['RegisteredName'], inst['RegisteredVersion']))

def main():

    if len(sys.argv) < 4:
        print("Usage: %s server_url username password" % sys.argv[0])
        sys.exit(2)

    server_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    explore_server(server_url, username, password)

    return 0

if __name__ == '__main__':
    sys.exit(main())
