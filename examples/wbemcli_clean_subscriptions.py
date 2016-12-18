"""
Wbemcli scriptlet that removes all subscriptions, filters, and destination
objects from the defined wbem connection
"""

from pywbem import WBEMServer


def display_path_info(descriptor, class_, namespace):
    """
    Display info on the instance names of the class parameter retrieved
    from the interop namespace of the server defined by CONN.

    The descriptor is text defining the class(ex. Filter)).
    Returns a list of the paths
    """
    paths = CONN.EnumerateInstanceNames(class_, namespace=interop)  # noqa: F821
    print('%ss: count=%s' % (descriptor, len(paths)))
    for path in paths:
        print('%s: %s' % (descriptor, path))
    return paths


def delete_paths(paths):
    """Delete all the CIMInstanceNames in paths paramter from the server."""
    for path in paths:
        CONN.DeleteInstance(path)  # noqa: F821


MY_SERVER = WBEMServer(CONN)  # noqa: F821
interop = MY_SERVER.interop_ns
print('Interop namespace=%s' % interop)

filter_paths = display_path_info("Filter", 'CIM_IndicationFilter', interop)
dest_paths = display_path_info("Destination", 'CIM_ListenerDestination',
                               interop)
sub_paths = display_path_info("Subscription", 'CIM_IndicationSubscription',
                              interop)

# If any paths exist, remove them and then redisplay the results
if filter_paths or dest_paths or sub_paths:

    delete_paths(sub_paths)
    delete_paths(dest_paths)
    delete_paths(filter_paths)

    filter_paths = display_path_info("Filter", 'CIM_IndicationFilter', interop)
    dest_paths = display_path_info("Destination", 'CIM_ListenerDestination',
                                   interop)
    sub_paths = display_path_info("Subscription", 'CIM_IndicationSubscription',
                                  interop)

print('Quit Scriplet. Quiting wbemcli')
quit()
