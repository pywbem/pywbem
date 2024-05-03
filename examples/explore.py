#!/usr/bin/env python

import sys

from pywbem import WBEMConnection, WBEMServer, ValueMapping

def print_profile_info(org_vm, inst):
    """Print the registered org, name, version for the profile defined by
       inst
    """
    org = org_vm.tovalues(inst['RegisteredOrganization'])
    name = inst['RegisteredName']
    vers = inst['RegisteredVersion']
    print(f"  {org} {name} Profile {vers}")

def explore_server(server_url, username, password):
    """ Demo of exploring a cim server for characteristics defined by
        the server class
    """

    print(f"WBEM server URL:\n  {server_url}")

    conn = WBEMConnection(server_url, (username, password),
                          no_verification=True)
    server = WBEMServer(conn)

    print(f"Brand:\n  {server.brand}")
    print(f"Version:\n  {server.version}")
    print(f"Interop namespace:\n  {server.interop_ns}")

    print("All namespaces:")
    for ns in server.namespaces:
        print(f"  {ns}")

    print("Advertised management profiles:")
    org_vm = ValueMapping.for_property(server, server.interop_ns,
                                       'CIM_RegisteredProfile',
                                       'RegisteredOrganization')
    for inst in server.profiles:
        print_profile_info(org_vm, inst)

    indication_profiles = server.get_selected_profiles('DMTF', 'Indications')

    print('Profiles for DMTF:Indications')
    for inst in indication_profiles:
        print_profile_info(org_vm, inst)

    server_profiles = server.get_selected_profiles('SNIA', 'Server')

    print('Profiles for SNIA:Server')
    for inst in server_profiles:
        print_profile_info(org_vm, inst)

    # get Central Instances
    for inst in indication_profiles:
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        vers = inst['RegisteredVersion']
        print(f"Central instances for profile {org}:{name}:{vers} "
              "(component):")
        try:
            ci_paths = server.get_central_instances(
                inst.path,
                "CIM_IndicationService", "CIM_System", ["CIM_HostedService"])
        except Exception as exc:
            print(f"Error: {exc}")
            ci_paths = []
        for ip in ci_paths:
            print(f"  {ip}")

    for inst in server_profiles:
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        vers = inst['RegisteredVersion']
        print(f"Central instances for profile {org}:{name}:{vers}(autonomous):")

        try:
            ci_paths = server.get_central_instances(inst.path)
        except Exception as exc:
            print(f"Error: {exc}")
            ci_paths = []
        for ip in ci_paths:
            print("  {ip}")

def main():

    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} server_url username password")
        sys.exit(2)

    server_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    explore_server(server_url, username, password)

    return 0

if __name__ == '__main__':
    sys.exit(main())
