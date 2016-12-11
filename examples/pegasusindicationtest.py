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
import os
import time
import threading
import logging
import datetime
from socket import getfqdn
if sys.version_info >= (3, 0):
    from urllib.parse import urlparse
if sys.version_info < (3, 0) and sys.version_info >= (2, 5):
    from urlparse import urlparse
from pywbem import WBEMConnection, WBEMServer, WBEMListener, CIMClassName, \
                   Error, ConnectionError, Uint32, WBEMSubscriptionManager

# definition of the filter.  This is openpegasus specific and uses
# a class that generates one indication for each call of a method
TEST_CLASS = 'Test_IndicationProviderClass'
TEST_CLASS_NAMESPACE = 'test/TestProvider'
TEST_QUERY = 'SELECT * from %s' % TEST_CLASS

# global count of indications recived by the local indication processor
RECEIVED_INDICATION_COUNT = 0
COUNTER_LOCK = threading.Lock()
LISTENER = None

INDICATION_START_TIME = None
LAST_INDICATION_TIME = None
MAX_TIME_BETWEEN_INDICATIONS = None
LAST_SEQ_NUM = None

LOGFILE = 'pegasusindicationtest.log'


def consume_indication(indication, host):
    """This function gets called when an indication is received.
       Depends on logger inside listener for output
    """

    #pylint: disable=global-variable-not-assigned
    global RECEIVED_INDICATION_COUNT, LISTENER, INDICATION_START_TIME, \
           LAST_INDICATION_TIME, MAX_TIME_BETWEEN_INDICATIONS, LAST_SEQ_NUM
    # increment count.
    COUNTER_LOCK.acquire()
    if INDICATION_START_TIME is None:
        INDICATION_START_TIME = datetime.datetime.now()

    if LAST_INDICATION_TIME is not None:
        time_diff = datetime.datetime.now() - LAST_INDICATION_TIME
        if MAX_TIME_BETWEEN_INDICATIONS is None:
            MAX_TIME_BETWEEN_INDICATIONS = time_diff
        elif time_diff > MAX_TIME_BETWEEN_INDICATIONS:
            MAX_TIME_BETWEEN_INDICATIONS = time_diff
    seq_num = indication['SequenceNumber']
    if LAST_SEQ_NUM is None:
        LAST_SEQ_NUM = seq_num
    else:
        if seq_num != (LAST_SEQ_NUM + 1):
            print('Missed %s indications at %s' % (((seq_num - 1) - LAST_SEQ_NUM),
                                                   LAST_SEQ_NUM))
        LAST_SEQ_NUM = seq_num

    LAST_INDICATION_TIME = datetime.datetime.now()

    RECEIVED_INDICATION_COUNT += 1
    #sys.stdout.write('.')
    #sys.stdout.flush()
    LISTENER.logger.info("Consumed CIM indication #%s: host=%s\n%s",
                         RECEIVED_INDICATION_COUNT, host, indication.tomof())
    COUNTER_LOCK.release()


def wait_for_indications(requested_indications):
    """
    Wait for indications to be received Time depends on indication count
    assume 20 per sec. Loop looks once per sec for all indications
    received but terminates after wait_time seconds.
    In addition it looks for idle indication count.  If the count has not
    moved in 10 seconds, it breaks the wait loop.
    Returns True if wait successful and counts match
    """

    last_indication_count = 0
    counter = 0
    try:
        success = False
        wait_time = int(requested_indications / 20) + 3
        stall_ct = 40           # max time period with no reception.
        for _ in range(wait_time):
            time.sleep(1)
            if last_indication_count != RECEIVED_INDICATION_COUNT:
                last_indication_count = RECEIVED_INDICATION_COUNT
                counter = 0

            # exit loop if all indications recieved.
            if RECEIVED_INDICATION_COUNT >= requested_indications:
                elapsed_time = LAST_INDICATION_TIME - INDICATION_START_TIME
                ind_per_sec = 0
                if elapsed_time.total_seconds() != 0:
                    ind_per_sec = \
                        RECEIVED_INDICATION_COUNT / elapsed_time.total_seconds()
                print('Rcvd %s indications, time=%s; %02.f per sec. '
                      'Exit wait loop' %
                      (RECEIVED_INDICATION_COUNT, elapsed_time, ind_per_sec))
                success = True
                break
            counter += 1
            if counter > stall_ct:
                elapsed_time = LAST_INDICATION_TIME - INDICATION_START_TIME
                ind_per_sec = 0
                if elapsed_time.total_seconds() != 0:
                    ind_per_sec = \
                        RECEIVED_INDICATION_COUNT / elapsed_time.total_seconds()
                print('Nothing received for %s sec: received=%s time=%s' \
                      ' %02.f per sec' % \
                      (stall_ct, RECEIVED_INDICATION_COUNT,
                       elapsed_time.total_seconds(), ind_per_sec))
                break

    # because this can be a long loop, catch cntrl-c
    except KeyboardInterrupt:
        print('Ctrl-C terminating wait loop early')

    # If success, wait and recheck to be sure no extras received.
    if success:
        time.sleep(2)
        if RECEIVED_INDICATION_COUNT != requested_indications:
            print('ERROR. Extra indications received')
    return success

def send_request_for_indications(conn, class_name, requested_indications):
    """
    Send an invokemethod to the WBEM server to initiate the indication
    output.  This is a pegasus specific operation. Note also that the
    way Pegasus works today, often the response for this request does not
    get returned until well after the indication flow has started because
    it operates on the same thread as the response.
    """
    try:
        # Send method to pegasus server to create  required number of
        # indications. This is a pegasus specific class and method

        result = conn.InvokeMethod("SendTestIndicationsCount", class_name,
                                   [('indicationSendCount',
                                     Uint32(requested_indications))])

        if result[0] != 0:
            print('SendTestIndicationCount Method error. Nonzero return=%s' \
                  % result[0])
            return False
        return True

    except Error as er:
        print('Error: Indication Method exception %s' % er)
        return False


def run_test(svr_url, listener_host, user, password, http_listener_port, \
             https_listener_port, requested_indications, repeat_loop):
    """
        Runs a test that:
        1. Creates a server
        2. Creates a dynamic listener and starts ti
        3. Creates a filter and subscription
        4. Calls the server to execute a method that creates an indication
        5. waits for indications to be received.
        6. Removes the filter and subscription and stops the listener
    """
    if os.path.exists(LOGFILE):
        os.remove(LOGFILE)
    try:
        conn = WBEMConnection(svr_url, (user, password), no_verification=True)
        server = WBEMServer(conn)

        # Create subscription_manager here to be sure we can communicate with
        # server before Creating listener, etc.
        sub_mgr = WBEMSubscriptionManager(
            subscription_manager_id='pegasusIndicationTest')

        # Add server to subscription manager
        server_id = sub_mgr.add_server(server)
        old_filters = sub_mgr.get_all_filters(server_id)
        old_subs = sub_mgr.get_all_subscriptions(server_id)
        # TODO filter for our sub mgr
        if len(old_subs) != 0 or len(old_filters) != 0:
            sub_mgr.remove_subscriptions(server_id,
                                         [inst.path for inst in old_subs])
            for filter_ in old_filters:
                sub_mgr.remove_filter(server_id, filter_.path)

    except ConnectionError as ce:
        print('Connection Error %s with %s' % (ce, svr_url))
        sys.exit(2)

    except Error as er:
        print('Error communicationg with WBEMServer %s' % er)
        sys.exit(1)

    # Create the listener and listener call back and start the listener
    #pylint: disable=global-statement
    global LISTENER
    ####stream=sys.stderr,
    logging.basicConfig(filename='pegasusindicationtest.log',
                        level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s')
    # Create and start local listener
    LISTENER = WBEMListener(listener_host, http_port=http_listener_port,
                            https_port=https_listener_port)

    # Start connect and start listener.
    LISTENER.add_callback(consume_indication)
    LISTENER.start()

    listener_url = '%s://%s:%s' % ('http', 'localhost', http_listener_port)
    sub_mgr.add_listener_destinations(server_id, listener_url)

    # Create a dynamic alert indication filter and subscribe for it
    filter_ = sub_mgr.add_filter(
        server_id, TEST_CLASS_NAMESPACE,
        TEST_QUERY,
        query_language="DMTF:CQL")
    subscriptions = sub_mgr.add_subscriptions(server_id, filter_.path)

    # Request server to create indications by invoking method
    # This is pegasus specific
    class_name = CIMClassName(TEST_CLASS, namespace=TEST_CLASS_NAMESPACE)

    while repeat_loop > 0:
        repeat_loop += -1
        global RECEIVED_INDICATION_COUNT, INDICATION_START_TIME
        RECEIVED_INDICATION_COUNT = 0
        INDICATION_START_TIME = None
        if send_request_for_indications(conn, class_name,
                                        requested_indications):
            # Wait for indications to be received.
            success = wait_for_indications(requested_indications)
            if not success:
                insts = conn.EnumerateInstances('PG_ListenerDestinationQueue',
                                                namespace='root/PG_Internal')
                for inst in insts:
                    print('%s queueFullDropped %s, maxretry %s, InQueue %s' % \
                          (inst['ListenerDestinationName'],
                           inst['QueueFullDroppedIndications'],
                           inst['RetryAttemptsExceededIndications'],
                           inst['CurrentIndications']))
        if repeat_loop > 0:
            time.sleep(requested_indications/150)


    sub_mgr.remove_subscriptions(server_id,
                                 [inst.path for inst in subscriptions])
    sub_mgr.remove_filter(server_id, filter_.path)
    sub_mgr.remove_server(server_id)
    LISTENER.stop()

    # Test for all expected indications received.
    if RECEIVED_INDICATION_COUNT != requested_indications:
        print('Incorrect count of indications received expected=%s, received'
              '=%s' % (requested_indications, RECEIVED_INDICATION_COUNT))
        sys.exit(1)
    else:
        print('Success, %s indications' % requested_indications)
    print('Max time between indications %s' % MAX_TIME_BETWEEN_INDICATIONS)


def main():
    """Setup parameters for the test and call the test function
        This is a very simple interface with fixed cli arguments. If there
        are no arguments it defaults to a standard internal set of
        arguments
    """

    if len(sys.argv) < 7:
        print("Requires fixed set of arguments or defaults to internally\n "
              "defined arguments.\n"
              "Usage: %s <url> <username> <password> <indication-count>" \
              "Where: <url> server url, ex. http://localhost\n" \
              "       <port> http listener port, ex. 5000\n" \
              "       <username> username for authentication\n" \
              "       <password> password for authentication\n" \
              "       <indication-count> Number of indications to request.\n" \
              "       <repeat_loop>   Repeat the send test repeat_loop times.\n"
              "Ex: %s http://fred 5000 blah blah 1000 10 " \
              % (sys.argv[0], sys.argv[0]))
        server_url = 'http://localhost'
        username = 'blah'
        password = 'blah'
        http_listener_port = 5000
        requested_indications = 1000
        repeat_loop = 1

    else:
        server_url = sys.argv[1]
        http_listener_port = int(sys.argv[2])
        username = sys.argv[3]
        password = sys.argv[4]
        requested_indications = int(sys.argv[5])
        repeat_loop = int(sys.argv[6])

    listener_addr = urlparse(server_url).netloc

    print('url=%s listener=%s port=%s usr=%s pw=%s cnt=%s repeat=%s' % \
          (server_url, listener_addr, http_listener_port, \
           username, password, requested_indications, repeat_loop))

    #https_listener_port = http_listener_port + 1
    https_listener_port = None

    run_test(server_url, listener_addr, username, password,
             http_listener_port, https_listener_port,
             requested_indications, repeat_loop)

    return 0


if __name__ == '__main__':
    sys.exit(main())
