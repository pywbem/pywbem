"""
Wbemcli scriptlet displays the number of subscriptions, filters, and
distination objects on the defined server and the list of instance paths.
"""

from pywbem import WBEMServer, WBEMSubscriptionManager


def display_paths(instances, type_str):
    """Display the count and paths for the list of instances in instances."""
    print('%ss: count=%s' % (type_str, len(instances),))
    for path in [instance.path for instance in instances]:
        print('%s: %s' % (type_str, path))
    if len(instances):
        print('')


MY_SERVER = WBEMServer(CONN)  # noqa: F821
print('Interop namespace=%s' % MY_SERVER.interop_ns)

with WBEMSubscriptionManager('fred') as sub_mgr:
    server_id = sub_mgr.add_server(MY_SERVER)

    display_paths(sub_mgr.get_all_filters(server_id), 'Filter')

    display_paths(sub_mgr.get_all_destinations(server_id), 'Destination')

    display_paths(sub_mgr.get_all_subscriptions(server_id), 'Subscription')

print('Quit Scriplet. Quiting wbemcli')
quit()
