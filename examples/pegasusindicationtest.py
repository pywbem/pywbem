#!/usr/bin/env python

"""
Example of handling subscriptions and indications from a particular
provider in OpenPegasus. This example depends on a test class and
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
import datetime
from socket import getfqdn
from urlparse import urlparse
from pywbem import WBEMConnection, WBEMServer, WBEMListener, CIMClassName, \
                   Error, Uint32, WBEMSubscriptionManager

# definition of the filter.  This is openpegasus specific and uses
# a class that generates one indication for each call of a method
TEST_CLASS = 'Test_IndicationProviderClass'
TEST_CLASS_NAMESPACE = 'test/TestProvider'
TEST_QUERY = 'SELECT * from %s' % TEST_CLASS

# global count of indications recived by the local indication processor
RECEIVED_INDICATION_COUNT = 0
LISTENER = None

class ElapsedTimer(object):
    """
        Set up elapsed time timer. Calculates time between initiation
        and access.
    """
    def __init__(self):
        """ Initiate the object with current time"""
        self.start_time = datetime.datetime.now()

    def reset(self):
        """ Reset the start time for the timer"""
        self.start_time = datetime.datetime.now()

    def elapsed_ms(self):
        """ Get the elapsed time in milliseconds. returns floating
            point representation of elapsed time in seconds.
        """
        dt = datetime.datetime.now() - self.start_time
        return ((dt.days * 24 * 3600) + dt.seconds) * 1000  \
                + dt.microseconds / 1000.0

    def elapsed_sec(self):
        """ get the elapsed time in seconds. Returns floating
            point representation of time in seconds
        """
        return self.elapsed_ms() / 1000

def consume_indication(indication, host):
    """This function gets called when an indication is received.
       Depends on logger inside listener for output
    """

    #pylint: disable=global-variable-not-assigned
    global RECEIVED_INDICATION_COUNT, LISTENER
    # increment count. This is thread safe because of GIL
    RECEIVED_INDICATION_COUNT += 1

    LISTENER.logger.debug("Consumed CIM indication #%s: host=%s\n%s",
                          RECEIVED_INDICATION_COUNT, host, indication.tomof())

def wait_for_indications(requested_indications):
    """
    Wait for indications to be received Time depends on indication count
    assume 5 per sec. Loop looks once per sec for all indications
    received but terminates after wait_time seconds.
    In addition it looks for idle indication count.  If the count has not
    moved in 30 seconds, it breaks the wait loop.
    Returns True if wait successful and counts match
    """
    last_indication_count = 0
    counter = 0
    starttime = ElapsedTimer()
    try:
        success = False
        wait_time = int(requested_indications / 5) + 3
        for _ in range(wait_time):
            if last_indication_count != RECEIVED_INDICATION_COUNT:
                last_indication_count = RECEIVED_INDICATION_COUNT
                counter = 0

            time.sleep(1)

            # exit loop if all indications recieved.
            if RECEIVED_INDICATION_COUNT >= requested_indications:
                elapsed_time = starttime.elapsed_sec()
                ind_per_sec = 0
                if elapsed_time != 0:
                    ind_per_sec = RECEIVED_INDICATION_COUNT/elapsed_time
                print('Rcvd %s indications in %s sec; %02.f per sec. '\
                      'Exit wait loop' % \
                      (RECEIVED_INDICATION_COUNT, elapsed_time, ind_per_sec))
                success = True
                break
            counter += 1
            if counter > 30:
                print('Indication reception stalled at received=%s' %
                      RECEIVED_INDICATION_COUNT)
                break

    except KeyboardInterrupt:
        print('Ctrl-C terminating wait loop early')

    # If success, wait and recheck to be sure no extras received.
    if success:
        time.sleep(2)
        if RECEIVED_INDICATION_COUNT != requested_indications:
            print('ERROR. Extra indications received')
    return success


def run_test(svr_url, listener_host, user, password, http_listener_port, \
             https_listener_port, requested_indications):
    """
        Runs a test that:
        1. Creates a server
        2. Creates a dynamic listener and starts ti
        3. Creates a filter and subscription
        4. Calls the server to execute a method that creates an indication
        5. waits for indications to be received.
        6. Removes the filter and subscription and stops the listener
    """


    conn = WBEMConnection(svr_url, (user, password), no_verification=True)
    server = WBEMServer(conn)

    # Create the listener and listener call back and start the listener

    #pylint: disable=global-statement
    global LISTENER

    # Create and start local listener
    LISTENER = WBEMListener(listener_host, http_port=http_listener_port,
                            https_port=https_listener_port)
    #start connect and start listener. Comment next lines for separate listener
    LISTENER.add_callback(consume_indication)
    LISTENER.start()

    # set up listener logger
    hdlr = logging.FileHandler('pegasusindications.log')
    hdlr.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    LISTENER.logger.addHandler(hdlr)

    #create subscription_manager
    subscription_manager = WBEMSubscriptionManager(
        subscription_manager_id='fred')

    # add server to subscription manager
    server_id = subscription_manager.add_server(server)
    listener_url = '%s://%s:%s' % ('http', 'localhost', http_listener_port)
    subscription_manager.add_listener_destinations(server_id, listener_url)

    #determine if there are any existing filters and display them
    existing_filters = subscription_manager.get_owned_filters(server_id)
    if len(existing_filters) != 0:
        print('%s filters exist in server' % len(existing_filters))
        for _filter in existing_filters:
            print('existing filter %s', _filter.tomof())

    # Create a dynamic alert indication filter and subscribe for it
    filter_path = subscription_manager.add_filter(
        server_id, TEST_CLASS_NAMESPACE,
        TEST_QUERY,
        query_language="DMTF:CQL")
    subscription_paths = subscription_manager.add_subscriptions(server_id,
                                                                filter_path)
    # request server to create indications by invoking method
    # This is pegasus specific
    class_name = CIMClassName(TEST_CLASS, namespace=TEST_CLASS_NAMESPACE)

    try:
        # Send method to pegasus server to create  required number of
        # indications. This is a pegasus specific class and method
        result = conn.InvokeMethod("SendTestIndicationsCount", class_name,
                                   [('indicationSendCount',
                                     Uint32(requested_indications))])

        if result[0] != 0:
            print('SendTestIndicationCount Method error. Nonzero return=%s' \
                  % result[0])
            sys.exit(1)

    except Error as er:
        print('Indication Method exception %s' % er)
        subscription_manager.remove_subscriptions(server_id,
                                                  subscription_paths)
        subscription_manager.remove_filter(server_id, filter_path)
        subscription_manager.remove_server(server_id)
        LISTENER.stop()
        sys.exit(1)

    # wait for indications to be received. Time based on number of indications
    wait_for_indications(requested_indications)

    subscription_manager.remove_subscriptions(server_id, subscription_paths)
    subscription_manager.remove_filter(server_id, filter_path)
    subscription_manager.remove_server(server_id)
    LISTENER.stop()

    # Test for all expected indications received.
    if RECEIVED_INDICATION_COUNT != requested_indications:
        print('Incorrect count of indications received expected=%s, received'
              '=%s' % (requested_indications, RECEIVED_INDICATION_COUNT))
        sys.exit(1)
    else:
        print('Success, %s indications' % requested_indications)


def main():
    """Setup parameters for the test and call the test function
        This is a very simple interface with fixed cli arguments. If there
        are no arguments it defaults to a standard internal set of
        arguments
    """

    if len(sys.argv) < 6:
        print("Requires fixed set of arguments or defaults to internally\n "
              "defined arguments.\n"
              "Usage: %s <url> <username> <password> <indication-count>" \
              "Where: <url> server url, ex. http://localhost\n" \
              "       <port> http listener port, ex. 5000\n" \
              "       <username> username for authentication\n" \
              "       <password> password for authentication\n" \
              "       <indication-count> Number of indications to request.\n" \
              "Ex: %s http://fred 5000 blah blah 100 " \
              % (sys.argv[0], sys.argv[0]))
        server_url = 'http://localhost'
        username = 'blah'
        password = 'blah'
        http_listener_port = 5000
        requested_indications = 100
    else:
        server_url = sys.argv[1]
        http_listener_port = int(sys.argv[2])
        username = sys.argv[3]
        password = sys.argv[4]
        requested_indications = int(sys.argv[5])

    listener_addr = urlparse(server_url).netloc

    print('url=%s listener=%s port=%s usr=%s pw=%s cnt=%s' % \
          (server_url, listener_addr, http_listener_port, \
           username, password, requested_indications))

    #https_listener_port = http_listener_port + 1
    https_listener_port = None

    run_test(server_url, listener_addr, username, password,
             http_listener_port, https_listener_port,
             requested_indications)

    return 0


if __name__ == '__main__':
    sys.exit(main())
