#!/usr/bin/env python

"""
Example of handling subscriptions and indications and receiving indications
from a particular provider in OpenPegasus . This example depends on a test
class and method in OpenPegasus.  It creates a server and a listener, starts
the listener and then requests the indications from the server. It waits for a
defined time for all indications to be received and then terminates either
normally if all are received or in error if not all were received.

This example:

1. Only handles http WBEM server and listener because parameters do not allow
   certificates.
"""
from __future__ import print_function, absolute_import

import sys
import os
import time
import logging
import datetime
import argparse

# pylint: disable=consider-using-f-string


from pywbem import WBEMConnection, WBEMServer, WBEMListener, CIMClassName, \
    Error, ConnectionError, Uint32, WBEMSubscriptionManager

from pywbem import configure_logger


def current_time():
    return time.strftime("%H:%M:%S", time.localtime())


class RunIndicationTest(object):  # pylint: disable=too-many-instance-attributes
    """
    Runs a test that:
    1. Creates a server
    2. Creates a dynamic listener and starts it.
    3. Creates a filter and subscription
    4. Calls the server to execute a method that creates an indication
    5. waits for indications to be received.
    6. Removes the filter and subscription and stops the listener
    """

    # Definition of the indicationfilter.  This is openpegasus specific and uses
    # a class that generates one indication for each call of a method
    indication_test_class = 'Test_IndicationProviderClass'
    test_class_namespace = 'test/TestProvider'
    test_query = 'SELECT * from %s' % indication_test_class

    # If set, outputs all of the requests (apis and html) and responses to
    # pywbem log file. This is not same log as the listener output.
    output_pywbem_log = False

    def __init__(self, svr_url, indication_destination_host, listener_host,
                 http_listener_port, user, password,
                 requested_indications, repeat_loop, output_log, verbose):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-arguments
        """
        Sets up and runs the indication test and removes subscriptions at the
        completion of the test.  There no return from this instance, it
        closes with the test complete or with an exception if the setup
        or test fails.

        Parameters:

            svr_url (:term:`string`):
                url of the target WBEM server. This must be an OpenPegasus
                server because the indication generator is defined as part
                of that server

            indication_destination_host ():
                host name/ip address where containing the listener.  This is
                the address to where indications are sent by the WBEM server.
                If the WBEM server is on a different system or in a container
                this must be an address usable by that system/container.
                Localhost is not a valid host name in that case.

            listener_host (:term:`string`):
                host name/ip address that will be used by the listener as
                its bind address or None. If this parameter contains
                a string that will be passed to WBEMListener as the host
                parameter. That name/IP address is used by the the socket
                services to only accept indications addressed to that
                network interface or IP address (depening on the OS, network,
                etc.)
                If None the listener will be forwarded indications addressed
                to any IP address in the containing computer system.

            http_listener_port (:term:`number`):
                listener port for indications sent with http.

            user (:term:`string`)
                Name of WBEM server user if required by WBEM server

            password (:term:`string`)
                Name of WBEM server password if required by WBEM server

            request_indications (:term:`number`):
                Number of indications requested from server for. The default
                is 1 indication.

            repeat_loop (:term:`number`):
                The number of times the request indications method is to
                be sent to the server.  It is sent to request that the
                server generate the number of indications defined by the
                request_indications parameter and when that number of
                indications has been received

            output_log (:class:`py:bool`):
                Flag to indicate whether the server should generate a log.

            verbose (:class:`py:bool`):
                Flag that when set generates diagnostic displays as the
                test proceedes.
        """

        # Test config parameters
        self.svr_url = svr_url
        self.indication_destination_host = indication_destination_host
        self.listener_host = listener_host
        self.http_listener_port = http_listener_port
        self.requested_indications = requested_indications
        self.repeat_loop = repeat_loop
        self.verbose = verbose
        self.logfile = 'pegasusindicationtest.log'

        # Define WBEM server CIMClassName for test indication class
        self.indication_test_class_name = \
            CIMClassName(self.indication_test_class,
                         namespace=self.test_class_namespace)

        # subscription server_id
        self.server_id = None

        # Test status parameters
        self.listener = None
        self.received_indication_count = 0

        # Test indication timers, and sequence number
        self.indication_start_time = None
        self.last_indication_time = None
        self.max_time_between_indications = None
        self.last_seq_num = None

        # Setup test
        if output_log:
            if self.verbose:
                print("Configure pywbem logger to a file.")
            configure_logger('all', log_dest='file', detail_level='all',
                             connection=True)

        # Define the ids of the subscription manager, destination and listener
        sub_mgr_id = 'pywbempegasusIndicationTest'
        self.subscription_destination_id = "dest1"
        self.subscription_filter_id = "filter1"

        if os.path.exists(self.logfile):
            if verbose:
                print("Removing old indication logfile {}".format(self.logfile))
            os.remove(self.logfile)

        logging.basicConfig(filename='pegasusindicationtest.log',
                            level=logging.INFO,
                            format='%(asctime)s %(levelname)s: %(message)s')

        try:
            # Setup wbem server and WBEMServer instance
            self.conn = WBEMConnection(svr_url, (user, password),
                                       no_verification=True)
            server = WBEMServer(self.conn)

            # Create subscription_manager here to be sure we can communicate
            # with server before Creating listener, etc.
            sub_mgr = WBEMSubscriptionManager(
                subscription_manager_id=sub_mgr_id)
            self.server_id = sub_mgr.add_server(server)

            # Remove existing subscriptions, destinations and filters
            # for this server_id since we want to rebuild from
            # scratch. This example uses only owned subscriptions, filters, and
            # destinations.  This only does anything in the odd case where
            # we fail during test and do not clean up at end of test.
            self.remove_existing_subscriptions(sub_mgr, self.server_id)

        except ConnectionError as ce:  # pylint: disable=invalid-name
            print('Connection Error {} with {}'.format(ce, svr_url))
            sys.exit(2)

        except Error as er:  # pylint: disable=invalid-name
            print('Error communicationg with WBEMServer {}'.format(er))
            sys.exit(1)

        self.create_listener()

        self.create_subscription(self.server_id, sub_mgr)

        # Run the test the number of times defined by repeat_loop
        success = self.repeat_test_loop(self.repeat_loop)

        # Remove server_id which removes owned subscriptions for this server_id
        sub_mgr.remove_server(self.server_id)

        self.listener.stop()

        completion_status = "Success" if success else "Failed"
        print("Indication test completed: {}".format(completion_status))

        # FUTURE/KS: This code is misplaced and should be removed or a better
        # summary result built.  I.e. This should be summary of complete test.
        # Test for all expected indications received.
        # if self.received_indication_count != self.requested_indications:
        #    print('Incorrect count of indications received expected={}, '
        #          'received={}'.format(self.requested_indications,
        #                               self.received_indication_count))
        #    sys.exit(1)
        # else:
        #    print('Test Success, {} indications received'.
        #          format(self.requested_indications))
        # print('Max time between indications {}'.
        #      format(self.max_time_between_indications))

    def create_listener(self):
        """
        Create the listener and listener call back and start the listener
        pylint: disable=global-statement
        """

        # Set the host to empty string if None to indicate no bind address
        # meaning that the listener will receive from any network interface.

        if self.listener_host is None:
            self.listener_host = ""

        self.listener = WBEMListener(self.listener_host,
                                     http_port=self.http_listener_port,
                                     https_port=None)

        # Start connect and start listener.
        self.listener.add_callback(self.consume_indication)

        if self.verbose:
            print("Starting listener\n {}".format(self.listener))
        self.listener.start()

    def create_subscription(self, server_id, sub_mgr):
        """
        Create the indication filter, indication destination and indication
        subscription from the instance variables. Displays the created objects
        if verbose set.
        """

        # Create the destination instance
        indication_dest_url = \
            "http://{0}:{1}".format(self.indication_destination_host,
                                    self.http_listener_port)

        destination = sub_mgr.add_destination(
            server_id, indication_dest_url,
            destination_id=self.subscription_destination_id)

        # Create a dynamic alert indication filter
        filter_ = sub_mgr.add_filter(server_id, self.test_class_namespace,
                                     self.test_query,
                                     query_language="DMTF:CQL",
                                     filter_id=self.subscription_filter_id)

        # Create the subscription
        subscriptions = sub_mgr.add_subscriptions(
            server_id, filter_.path, destination_paths=destination.path)

        if self.verbose:
            print("Subscription instances\n {0}\n{1}\n{2}".
                  format(filter_.tomof(), destination.tomof(),
                         subscriptions[0].tomof()))

    def repeat_test_loop(self, repeat_loop):
        """
        Send indication request to server repeatedly and wait for the
        expected number of indications. Returns only when all repeats completed.
        """

        while repeat_loop > 0:
            repeat_loop += -1
            self.received_indication_count = 0
            self.indication_start_time = None

            # pylint: disable=too-many-function-args
            self.send_request_for_indications(self.indication_test_class_name,
                                              self.requested_indications)

            success = self.receive_expected_indications()

            # test for success of receive indications. and possibly terminate
            if not success:
                print("Test failed. Terminating repeat loop.")
                return False

            # Sleep between each run of the test.
            if repeat_loop > 0:
                time.sleep(self.requested_indications / 150)

        return success

    def consume_indication(self, indication, host):
        """
        Consume a single indication. This is a callback and may be on another
        thead. It is called each time an indication is received.
        """
        # Count received indications and save received time.
        if self.indication_start_time is None:
            self.indication_start_time = datetime.datetime.now()

        # time for this indication
        if self.last_indication_time is not None:
            time_diff = datetime.datetime.now() - self.last_indication_time
            if self.max_time_between_indications is None:
                self.max_time_between_indications = time_diff
            elif time_diff > self.max_time_between_indications:
                self.max_time_between_indications = time_diff

        seq_num = indication['SequenceNumber']

        if self.last_seq_num is None:
            self.last_seq_num = seq_num
            self.received_indication_count = 1
        else:
            if seq_num != (self.last_seq_num + 1):
                print('Missed {0} indications at {1}'.
                      format(((seq_num - 1) - self.last_seq_num),
                             self.last_seq_num))
            self.last_seq_num = seq_num

            self.last_indication_time = datetime.datetime.now()

            self.received_indication_count += 1

        # pylint: disable=logging-format-interpolation
        self.listener.logger.info(
            "Consumed CIM indication #{}: host={}\n{}".
            format(self.received_indication_count, host,
                   indication.tomof()))

    def receive_expected_indications(self):
        """
        Wait for expected indications to be received.  If there is an
        error in the indications received, try to get more information from
        OpenPegasus.
        Returns True if successful reception, else False
        """
        # Wait for indications to be received.
        success = self.wait_for_indications()

        if not success:
            print("Wait for expected indications failed.\n"
                  "Attempting to display pegasus Indication dest queue.\n")

            insts = self.conn.EnumerateInstances('PG_ListenerDestinationQueue',
                                                 namespace='root/PG_Internal')
            for inst in insts:
                print('ListenerDestinationName={}:\n   QueueFullDropped={} , '
                      'RetryAttemptsExceeded={}, InQueue={}'
                      .format(inst['ListenerDestinationName'],
                              inst['QueueFullDroppedIndications'],
                              inst['RetryAttemptsExceededIndications'],
                              inst['CurrentIndications']))

                if self.verbose:
                    print("Full instnace of OpenPegasus dest queue:\n{}".
                          format(inst.tomof()))
        return success

    def wait_for_indications(self):
        """
        Wait for indications to be received. This waits for the expected number
        of indications to be received to match the request to the server and
        includes indication timers and  stall mechanism that will time out if
        no indication has been received in a reasonable amount of time.

        This method will also catch a terminal control-C and terminate this
        method early.

        Finally it waits for a couple of seconds after the receipt of the
        number of expected indications to see if there are any extra unexpected
        indications, flags that in a message but returns successful completion.
        """
        last_indication_count = 0
        return_flag = False
        stall_ctr = 0

        # Wait loop for reception of all of the indications for indication
        # request to the wbem server.  Try block allows ctrl-C exception
        try:
            return_flag = False
            #max_loop_ct = int(self.requested_indications / 20) + 3

            # Loop to wait for indications and exit if all received or
            # exceeds stall count.
            while True:
                time.sleep(1)

                # Finish processing if all requested indications received
                if self.received_indication_count >= self.requested_indications:
                    elapsed_time = \
                        self.last_indication_time - self.indication_start_time
                    ind_per_sec = 0
                    if elapsed_time.total_seconds() != 0:
                        ind_per_sec = self.received_indication_count / \
                            elapsed_time.total_seconds()
                    print('Rcvd {} indications, time={} sec, {:.2f} per sec'
                          .format(self.received_indication_count,
                                  elapsed_time.total_seconds(),
                                  ind_per_sec))
                    return_flag = True
                    break

                # If something received,  reloop, reset stall_ctr
                elif last_indication_count != self.received_indication_count:
                    last_indication_count = self.received_indication_count
                    stall_ctr = 0

                    print("Rcvd {} indications.".format(last_indication_count))
                    continue

                # Nothing received in last loop and requested number not rcvd.
                else:
                    stall_ctr += 1
                    if self.last_indication_time:
                        stalled_time = datetime.datetime.now() - \
                            self.last_indication_time
                    else:
                        stalled_time = datetime.datetime.now() - \
                            self.indication_start_time

                    if stall_ctr > 5:
                        if self.last_indication_time:
                            elapsed_time = \
                                self.last_indication_time - \
                                    self.indication_start_time
                        else:
                            elapsed_time = 0
                        if elapsed_time != 0:
                            ind_per_sec = self.received_indication_count / \
                                elapsed_time.total_seconds()
                        else:
                            ind_per_sec = 0

                        print('Nothing received for {} sec: received={} '
                              'time={} sec: {:.2f} per sec. stall ctr={}'.
                              format(stalled_time.total_seconds(),
                                     self.received_indication_count,
                                     elapsed_time.total_seconds(),
                                     ind_per_sec,
                                     stall_ctr))
                        break
                    else:
                        print("waiting {:.2f} sec. with no indications ct {}".
                              format(stalled_time.total_seconds(), stall_ctr))

        # Because this can be a long loop, catch CTRL-C
        except KeyboardInterrupt:
            print('Ctrl-C terminating wait loop early')

        # If return_flag True, wait and recheck to be sure no extras
        # received.
        if return_flag:
            time.sleep(2)
            if self.received_indication_count != self.requested_indications:
                print('ERROR. Extra indications received {}, requested {}'.
                      format(self.received_indication_count,
                             self.requested_indications))
        return return_flag

    def remove_existing_subscriptions(self, sub_mgr, server_id):
        """
        Remove any existing filters, destinations, and filters for the
        this server_id.
        """
        sub_mgr.remove_subscriptions(
            server_id,
            [inst.path for inst in sub_mgr.get_owned_subscriptions(server_id)])

        for filter_inst in sub_mgr.get_owned_filters(server_id):
            sub_mgr.remove_filter(server_id, filter_inst.path)

        sub_mgr.remove_destinations(
            server_id,
            [inst.path for inst in sub_mgr.get_owned_destinations(server_id)])

    def send_request_for_indications(self, class_name, indication_count):
        """
        Send an invokemethod to the WBEM server to initiate the indication
        output.  This is a pegasus specific invokemethod. Note also that the
        way Pegasus works today, often the response for this request does not
        get returned until well after the indication flow has started because
        it operates on the same thread as the response.

        Returns True if invokemethod accepted by server or False if not
        """
        try:
            # Send method to pegasus server to create  required number of
            # indications. This is a pegasus specific class and method
            send_indication_method = "SendTestIndicationsCount"
            send_count_param = 'indicationSendCount'

            if self.verbose:
                print("Send InvokeMethod to WBEM Server:")
                print("class_name {0} method {1} for {2} indications".
                      format(class_name, send_indication_method,
                             indication_count))

            result = self.conn.InvokeMethod(
                send_indication_method, class_name,
                [(send_count_param, Uint32(indication_count))])

            if result[0] != 0:
                print('Error: SendTestIndicationCount Method error. '
                      'Nonzero return from InvokeMethod={}'
                      .format(result[0]))
                return False
            return True

        except Error as er:  # pylint: disable=invalid-name
            print('Error: Indication Method exception {}'.format(er))
            return False


def usage(script_name):  # pylint: disable=missing-function-docstring
    return """
This example tests pywbem capability to create subscriptions in a WBEM server
and send indications from that server to a WBEM indication listener in
multiple environments.

{} creates a pywbem indication listener using the host name/IP address defined
by <dest_host> argument, <--port> and an indication subscription to the server
defined by <server-url> with listener destination address defined by
<--dest_host> and <--port> options.

It then sends a method to a OpenPegasus specific provider in the WBEM Server to
request that the server generate the number of indications defined by
<--indication-cnt>.

The listener monitors the received indications expecting the number
of indications defined by <indication-cnt> and displays whether the result was
correct or in error.

Finally, the test is repeated the number of times defined by <--repeat-loop>
option and then the indication subscription is removed from the host and
the listener closed.

This example handles only http connections since there are no parameters
for certificates.

This test only works with OpenPegasus because it uses an OpenPegasus
specific CIM class (Test_IndicationProviderClass) and provider to send
the indications.

""".format(script_name)


def examples(script_name):  # pylint: disable=missing-function-docstring
    examples_txt = """
EXAMPLES:
Simple wbem server in same network as client and using loopback:
    {0} localhost
    Tests with localhost as WBEM server on same host as pywbem using default
    listener port, etc. and listener port 5000

  Network on another network (ex. Docker container)
    {0} localhost:15988 -d 192.168.4.44
    Tests with localhost:15988 as WBEM server (ex. in Docker container)
    and 192.4.44 as IP address of listener that is availiable to WBEM
    server in the container.

  Network on network and listener IP address constrained
    {0} localhost:15988 -d 192.168.4.44 -l 192.168.4.44
    Tests with localhost:15988 as WBEM server (ex. in Docker container)
    and 192.4.44 as IP address of listener that is availiable to WBEM
    server in the container and listener IP bound to IP 192.168.4.44
""".format(script_name)
    return examples_txt


def main():
    """Setup parameters for the test and call the test function. This example
       includes parameters to allow the user to set the server url, indication
       destination host, listener port, and users/password. Note that it does
       not include parameters for certificates and only creates HTTP
       listeners.
    """
    prog = "pegasusindicationtest.py"
    parser = argparse.ArgumentParser(
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=usage(prog),
        epilog=examples(prog))

    parser.add_argument(
        "wbem_server_url",
        help="Url of server including port if required.  Does not include "
        "scheme since this is http only.")

    parser.add_argument(
        '-d', "--dest_host",
        help="Listener destination host name or IP address to be set into the "
             "subscription destination instance. This must be an IP address or "
             "hostname available to to the system containing the listener "
             "and the system containing the WBEM server.")

    parser.add_argument(
        '-l', "--listener_host", default=None,
        help="Optional host name or IP address for the indication listener.  "
        "This must be host system name or IP address available to both system "
        "containing listener and WBEM Server.  Listener will refuse "
        "indications on any other network address if this is set. Default is "
        "None which allows listener to receive on any defined network.")

    parser.add_argument(
        '-p', "--port", type=int, default=5000,
        help="Optional listener port used in both the subscription destination "
        "definition and the listener definition. Default is 5000")

    parser.add_argument(
        '-u', "--username", default="",
        help="Optional username for target server. Only used if server "
        "requires as user name.")

    parser.add_argument(
        '-w', "--password", default="",
        help="Optional password for target server. Required if --username "
        "defined")

    parser.add_argument(
        '-i', "--indication-count", type=int, default=1,
        help="Count of indications to be requested from WBEM Server.")

    parser.add_argument(
        '-r', "--repeat-loop", type=int, default=1,
        help="Count of times to repeat the test.")

    parser.add_argument(
        "--log", action='store_true',
        help="Generate pywbem log with details of all api calls requests "
        "to the server and responses.  File name is pywbem.log")

    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    if args.verbose:
        print(args)

    RunIndicationTest(args.wbem_server_url, args.dest_host, args.listener_host,
                      args.port, args.username, args.password,
                      args.indication_count, args.repeat_loop, args.log,
                      args.verbose)

    return 0


if __name__ == '__main__':
    sys.exit(main())
