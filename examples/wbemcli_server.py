"""
This wbemcli scriptlet creates a WBEMServer for the connection
This is not a separate script but a scriplet for wbemcli.
It implements the creation of a WBEMServer based on the CONN, the
creation of the org_valuemap for profiles and a print function to
display basic profile information.
"""

from pywbem import WBEMServer, ValueMapping


def print_profile_info(org_vm, profile_instance):
    """
    Print information on a profile defined by profile_instance.

    Parameters:

      org_vm: The value mapping for CIMRegisterdProfile and
          RegisteredOrganization so that the value and not value mapping
          is displayed.

      profile_instance: instance of a profile to be printed
    """
    org = org_vm.tovalues(profile_instance['RegisteredOrganization'])
    name = profile_instance['RegisteredName']
    vers = profile_instance['RegisteredVersion']
    print("  %s %s Profile %s" % (org, name, vers))

# Create the server and save in global SERVER
SERVER = WBEMServer(CONN)

# create the CIMRegisterd Profile ValueMapping for the
# defined server. This can be used to
org_vm = ValueMapping.for_property(SERVER, SERVER.interop_ns,
                                   'CIM_RegisteredProfile',
                                   'RegisteredOrganization')

print("Brand:\n  %s" % SERVER.brand)
print("Version:\n  %s" % SERVER.version)
print("Interop namespace:\n  %s" % SERVER.interop_ns)

for inst in SERVER.profiles:
    print_profile_info(org_vm, inst)
