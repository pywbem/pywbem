#!/usr/bin/env python

"""
Example of handling subscriptions and indications from a particular
provider in openpegasus. This example depends on a test class and
method in OpenPegasus.  It creates a server and a listener, starts
the listener and then requests the indications from the server.
It waits for a defined time for all indications to be received and
then terminates either normally if all are received or in error if
not all were received.

"""
from __future__ import print_function, absolute_import
import sys
import time
import logging
from socket import getfqdn
from pywbem import WBEMConnection, WBEMServer, WBEMListener, CIMClassName, \
                   Error, Uint32

# definition of the filter.  This is openpegasus specific and uses
# a class that generates one indication for each call of a method
TEST_CLASS = 'Test_IndicationProviderClass'
TEST_CLASS_NAMESPACE = 'test/TestProvider'
TEST_QUERY = 'SELECT * from %s' % TEST_CLASS

# global count of indications recived by the local indication processor
RECEIVED_INDICATION_COUNT = 0
LISTENER = None


def process_indication(indication, host):
    """This function gets called when an indication is received.
       Depends on logger inside listener for output
    """

    #pylint: disable=global-variable-not-assigned
    global RECEIVED_INDICATION_COUNT, LISTENER
    # increment count. This is thread safe because of GIL
    RECEIVED_INDICATION_COUNT += 1

    LISTENER.logger.info("++++++++++Received CIM indication #%s: host=%s\n%s",
                         RECEIVED_INDICATION_COUNT, host, indication)


def run_test(url, user, password, requested_indication_count, verbose):
    """
        Runs a test that:
        1. Creates a server
        2. Creates a dynamic listener and starts ti
        3. Creates a filter and subscription
        4. Calls the server to execute a method that creates an indication
        5. waits for indications to be received.
        6. Removes the filter and subscription, stop the listener, and stop
           the server.

    """

    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format= \
                        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    conn = WBEMConnection(url, (user, password), no_verification=True)
    server = WBEMServer(conn)

    # Set arbitrary port for the http listener
    http_listener_port = 50000

    # Create the listener and listener call back and start the listener

    global LISTENER
    LISTENER = WBEMListener(getfqdn(), http_port=http_listener_port,
                            https_port=None)

    # connect the listener callback, add to server, and start listener
    LISTENER.add_callback(process_indication)
    server_id = LISTENER.add_server(server)
    LISTENER.start()

    # set up listener logger.
    LISTENER.logger.addHandler(logging.StreamHandler())

    # define a logger for the client code below.
    client_log = logging.getLogger("Client")

    client_log.info('WBEMListener started http port %s ', http_listener_port)

    # Create a dynamic alert indication filter and subscribe for it
    filter_path = LISTENER.add_dynamic_filter(server_id, TEST_CLASS_NAMESPACE,
                                              TEST_QUERY,
                                              query_language="DMTF:CQL")

    subscription_path = LISTENER.add_subscription(server_id, filter_path)

    # request server to create indications by invoking method
    class_name = CIMClassName(TEST_CLASS, namespace=TEST_CLASS_NAMESPACE)
    try:
        # send method to server to create  required number of indications.
        # This is a pegasus specific class and method
        result = conn.InvokeMethod("SendTestIndicationsCount", class_name,
                                   [('indicationSendCount',
                                     Uint32(requested_indication_count))])

        if result[0] != 0:
            client_log.error('Method error. Nonzero return. %s', result[0])
            sys.exit(1)

    except Error as er:
        client_log.error('Indication Method exception %s', er)
        #TODO It would be more logical to eliminate the filter, subscription
        #     and listener at this point before we exit.
        sys.exit(1)

    # wait for indications to be received. Time depends on indication count
    # assume 5 per sec. Loop looks once per sec for all indications
    # received but terminates after wait_time seconds.
    # TODO this is a primitive wait loop but sufficient for testing.
    wait_time = int(requested_indication_count / 5) + 3
    for i in range(wait_time):
        time.sleep(1)
        # exit the loop if all indications recieved.
        if RECEIVED_INDICATION_COUNT == requested_indication_count:
            break

    # remove the subscription and filter
    LISTENER.remove_subscription(url, subscription_path)
    LISTENER.remove_dynamic_filter(server_id, filter_path)

    # time for any final indications to be received before stopping listener
    # Then stop the listener and remove the server.
    time.sleep(2)
    LISTENER.stop()
    LISTENER.remove_server(server_id)

    # Test for all expected indications received.
    if RECEIVED_INDICATION_COUNT != requested_indication_count:
        client_log.error('Insufficient indications received exp=%s recvd=%s',
                         requested_indication_count, RECEIVED_INDICATION_COUNT)
        sys.exit(1)


def main():
    """Setup parameters for the test and call the test function
        This is a very simple interface with fixed cli arguments. If there
        are no arguments it defaults to a standard internal set of
        arguments
    """

    if len(sys.argv) < 5:
        print("Requires fixed set of arguments or defaults to internally\n "
              "defined arguments.\n"
              "Usage: %s <url> <username> <password> <indication-count>" \
              "Where: <url> server url, ex. http://localhost\n" \
              "       <username> username for authentication\n" \
              "       <password> password for authentication\n" \
              "       <indication-count> Number of indications to request.\n" \
              "Ex: %s http://fred blah blah 100." \
              % (sys.argv[0], sys.argv[0]))
        sys.exit(2)
        server_url = 'localhost'
        username = 'blah'
        password = 'blah'
        requested_indication_count = 10
    else:
        server_url = sys.argv[1]
        username = sys.argv[2]
        password = sys.argv[3]
        requested_indication_count = int(sys.argv[4])

    verbose = True

    run_test(server_url, username, password, requested_indication_count,
             verbose)

    return 0


if __name__ == '__main__':
    sys.exit(main())
