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
    indications_profile = None
    server_profile = None
    for inst in server.profiles:
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        vers = inst['RegisteredVersion']
        print("  %s %s Profile %s" % (org, name, vers))
        if org == "DMTF" and name == "Indications":
            indications_profile = inst
        if org == "SNIA" and name == "Server":
            server_profile = inst

    if indications_profile is not None:
        print("Central instances for DMTF Indications profile (component):")
        try:
            ci_paths = server.get_central_instances(
                indications_profile.path,
                "CIM_IndicationService", "CIM_System", ["CIM_HostedService"])
        except Exception as exc:
            print("Error: %s" % str(exc))
            ci_paths = []
        for ip in ci_paths:
            print("  %s" % str(ip))

    if server_profile is not None:
        print("Central instances for SNIA Server profile (autonomous):")
        try:
            ci_paths = server.get_central_instances(server_profile.path)
        except Exception as exc:
            print("Error: %s" % str(exc))
            ci_paths = []
        for ip in ci_paths:
            print("  %s" % str(ip))

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
