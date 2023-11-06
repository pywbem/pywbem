#!/usr/bin/env python

"""
Example of handling subscriptions and indications and receiving indications
from a particular provider in OpenPegasus . This example depends on a test
class and method in OpenPegasus.  It creates a server and a listener, starts
the listener and then requests the indications from the server. It waits for a
defined time for all indications to be received and then terminates either
normally if all are received or in error if not all were received.

This is a complete example with cmd line argument parsing to set up parameters
for the test.  Use --help option to view cmd line parameters.

This example:

1. Only handles http WBEM server and listener because parameters do not include
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

# pylint: disable=redefined-builtin
from pywbem import WBEMConnection, WBEMServer, WBEMListener, CIMClassName, \
    Error, ConnectionError, AuthError, Uint32, \
    WBEMSubscriptionManager # noqa E402
# pylint: enable=redefined-builtin

from pywbem import configure_logger


def current_time():
    """get current time as string"""
    return time.strftime("%H:%M:%S", time.localtime())


class RunIndicationTest(object):
    # pylint: disable=too-many-instance-attributes, useless-object-inheritance
    """
    Sets up and runs the indication test and removes subscriptions at the
    completion of the test.  There no return from this instance, it
    closes with the test complete or with an exception if the setup
    or test fails. Uses class to simplify parameters for methods.

    Runs a test that:
    1. Creates a WBEM server connection
    2. Creates a dynamic listener and starts it.
    3. Creates a filter and subscription
    4. Calls the server to execute a method that creates indications
    5. waits for indications to be received.
    6. Removes the filter and subscription and stops the listener.
    """

    # Definition of the indicationfilter.  This is openpegasus specific and uses
    # a class that generates indications for each call of a method
    indication_test_class = 'Test_IndicationProviderClass'
    test_class_namespace = 'test/TestProvider'
    test_query = 'SELECT * from %s' % indication_test_class

    def __init__(self, wbem_conn, indication_destination_host,
                 listener_host, http_listener_port, requested_indications,
                 repeat_loop, verbose):
        # pylint: disable=too-many-locals, too-many-arguments
        """
        Parameters:

            wbem_conn (:class:`WBEMConnection`):
                connection object for the target WBEM server. This must be an
                OpenPegasus server because the indication generator is defined
                as part of that server

            indication_destination_host (:term:`string`):
                host name/ip address containing the listener.  This is
                the address to where indications are sent by the WBEM server.
                If the WBEM server is on a different system or in a container
                this must be an address usable by that system/container.
                Localhost is not a valid host name in that case.

            listener_host (:term:`string` or None):
                host name/ip address that will be used by the listener as its
                bind address. If this parameter contains a string that will be
                passed to WBEMListener as the host parameter. That name/IP
                address is used by socket services to accept only indications
                addressed to that network interface or IP address (depending on
                the OS, network, etc.). If None the listener will receive
                indications addressed to any IP address in the containing
                computer system.

            http_listener_port (:term:`number`):
                listener port for indications sent with http.

            request_indications (:term:`number`):
                Number of indications requested from server for. The default
                is 1 indication.

            repeat_loop (:term:`number`):
                The number of times the request indications method is to
                be sent to the server.  It is sent to request that the
                server generate the number of indications defined by the
                request_indications parameter and when that number of
                indications has been received

            verbose (:class:`py:bool`):
                Flag that when set generates diagnostic displays as the
                test proceedes.
        """
        # Test config parameters
        self.conn = wbem_conn
        self.indication_destination_host = indication_destination_host
        self.listener_host = listener_host
        self.http_listener_port = http_listener_port
        self.requested_indications = requested_indications
        self.repeat_loop = repeat_loop
        self.verbose = verbose
        if self.verbose:
            print("Listener indication_destination_host IP address {}".
                  format(self.indication_destination_host))

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
        self.received_indications = []

        # Define the ids of the subscription manager, destination and listener
        sub_mgr_id = 'pywbempegasusIndicationTest'
        self.subscription_destination_id = "dest1"
        self.subscription_filter_id = "filter1"

        try:
            # Setup WBEMServer instance for the WBEM connection
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

        except Error as er:  # pylint: disable=invalid-name
            print('Error {} communicating with WBEMServer {}'.
                  format(er, self.conn))
            sys.exit(1)

        self.create_listener()

        self.create_subscription(self.server_id, sub_mgr)

        # Run the test the number of times defined by repeat_loop
        success = self.repeat_test_loop(self.repeat_loop)

        # Remove server_id which removes owned subscriptions for this server_id
        if self.verbose:
            print("Remove subscriptions and stop listener.")
        sub_mgr.remove_server(self.server_id)
        self.listener.stop()

        completion_status = "Success" if success else "Failed"
        print("Indication test completed: {}".format(completion_status))
        if not success:
            sys.exit(1)

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
        self.listener.add_callback(self.indication_consumer)

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
        test_result = False
        while repeat_loop > 0:
            repeat_loop += -1
            self.received_indication_count = 0
            self.indication_start_time = None

            # pylint: disable=too-many-function-args
            self.send_request_for_indications(self.indication_test_class_name,
                                              self.requested_indications)

            test_result = self.receive_expected_indications()

            # Test for success of receive indications. and possibly terminate
            if not test_result:
                print("Test failed. Terminating repeat loop.")
                return False

            # Sleep between each run of the test.
            if repeat_loop > 0:
                time.sleep(self.requested_indications / 150)

        return test_result

    def indication_consumer(self, indication, host):
        """
        Consume a single indication. This is a callback and is on another
        thread from the script thread. It is called each time an indication
        is received.
        """
        self.received_indications.append(indication)
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

        rcvd_seq_num = indication['SequenceNumber']

        if self.last_seq_num is None:
            self.last_seq_num = rcvd_seq_num
            self.received_indication_count = 0
        else:
            exp_seq_num = self.last_seq_num + 1
            if rcvd_seq_num != exp_seq_num:
                missing_cnt = (rcvd_seq_num - 1) - self.last_seq_num
                print('Missed {0} indications at {1}, last rcvd seq num={2}, '
                      'exp seq num={2}'.format(missing_cnt, self.last_seq_num,
                                               exp_seq_num))

            self.last_seq_num = rcvd_seq_num

        self.last_indication_time = datetime.datetime.now()
        self.received_indication_count += 1

        # pylint: disable=logging-format-interpolation
        self.listener.logger.info(
            "Consumed CIM indication #{}: host={}\n{}".
            format(self.received_indication_count, host,
                   indication.tomof()))

    def display_pegasus_queue_info(self):
        """
        Try to display the information from the OpenPegasus internal queue
        of indications. This provides more information about the indications
        that did not get delivered, etc.
        """
        insts = self.conn.EnumerateInstances(
            'PG_ListenerDestinationQueue', namespace='root/PG_Internal')
        for inst in insts:
            print('ListenerDestinationName={}:\n   QueueFullDropped={} , '
                  'RetryAttemptsExceeded={}, InQueue={}'
                  .format(inst['ListenerDestinationName'],
                          inst['QueueFullDroppedIndications'],
                          inst['RetryAttemptsExceededIndications'],
                          inst['CurrentIndications']))

            if self.verbose:
                print("\nFull instance of OpenPegasus dest queue:\n{}".
                      format(inst.tomof()))

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
            self.display_pegasus_queue_info()
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
                    print('Rcvd {} indications, time={} sec, {:.1f} '
                          'indications/sec.'
                          .format(self.received_indication_count,
                                  elapsed_time.total_seconds(), ind_per_sec))
                    return_flag = True
                    break

                # If something received,  reloop, reset stall_ctr
                if last_indication_count != self.received_indication_count:
                    last_indication_count = self.received_indication_count
                    stall_ctr = 0

                    print("Rcvd {} indications.".format(last_indication_count))
                    continue

                # Nothing received in last loop and requested number not rcvd.
                stall_ctr += 1
                if self.last_indication_time:
                    stalled_time = datetime.datetime.now() - \
                        self.last_indication_time
                elif self.indication_start_time:
                    stalled_time = datetime.datetime.now() - \
                        self.indication_start_time

                else:
                    self.indication_starttime = datetime.datetime.now()
                    stalled_time = datetime.datetime.now() - \
                        datetime.datetime.now()

                if stall_ctr > 5:
                    if self.last_indication_time:
                        elapsed_time = \
                            self.last_indication_time - \
                            self.indication_start_time
                        ind_per_sec = self.received_indication_count / \
                            elapsed_time.total_seconds()
                        elapsed_time = elapsed_time.total_seconds()
                    else:
                        elapsed_time = 0
                        ind_per_sec = 0

                    print('Nothing received for {} sec: received={} '
                          'time={} sec: {:.2f} per sec. stall ctr={}'.
                          format(stalled_time.total_seconds(),
                                 self.received_indication_count,
                                 elapsed_time,
                                 ind_per_sec,
                                 stall_ctr))
                    break

                # NOTE: Leave this in until we resolve issue # 3022
                print("waiting {:.2f} sec. with no indications rcvd".
                      format(stalled_time.total_seconds()))

        # Because this can be a long loop, catch CTRL-C
        except KeyboardInterrupt:
            print('Ctrl-C terminating wait loop early')

        # If return_flag True, wait and recheck to be sure no extras
        # received.
        if return_flag:
            time.sleep(2)
            if self.received_indication_count != self.requested_indications:
                rcvd_ind_strs = [ind.tomof() for
                                 ind in self.received_indications]
                print('ERROR. Extra indications received {}, requested {}, '
                      'Received indications:\n{}'.
                      format(self.received_indication_count,
                             self.requested_indications,
                             "\n".join(rcvd_ind_strs)))
        return return_flag

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
                print("  class_name {0} method {1} for {2} indications".
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

    @staticmethod
    def remove_existing_subscriptions(sub_mgr, server_id):
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


def connect_wbem_server(wbem_server_url, username, password, timeout):
    """
    Create the WBEM server connection
    """
    if username and password:
        creds = (username, password)
    else:
        creds = None
    # NOTE: Does not test for existence of username or password.
    conn = WBEMConnection(wbem_server_url,
                          creds=creds,
                          timeout=timeout,
                          no_verification=True)
    try:
        conn.GetQualifier('Association')
    except ConnectionError as cd:
        print("Connection Error: {}. Connection to wbemserver {} failed".
              format(cd, wbem_server_url))
        sys.exit(1)
    except AuthError as ae:
        print("Auth Error: {}. Connection to wbemserver {} failed".
              format(ae, wbem_server_url))
        sys.exit(1)
    except Error:
        # Retest with EnumerateClassNames if Error received.
        try:
            conn.EnumerateClassNames()
        except Error as er1:
            print("Error: {}. Connection to wbemserver {} failed".
                  format(er1, wbem_server_url))
            sys.exit(1)
    return conn


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


def main():  # pylint: disable=too-many-branches
    """Setup parameters for the test and call the test function. This example
       includes parameters to allow the user to set the server url, indication
       destination host, listener port, and users/password. Note that it does
       not include parameters for certificates and only creates HTTP
       listeners.
    """
    prog_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(
        prog=prog_name,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=usage(prog_name),
        epilog=examples(prog_name))

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
        "This must be a host system name or IP address publically available to "
        "both the system containing listener and WBEM Server.  Listener will"
        " refuse indications on any other network address if this is set. "
        "Default is None which allows listener to receive on any network "
        "address defined for the local system.")

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
        "to the server and responses and for indications received.")

    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    # Setup logging for requests to server and indications if --log set
    basename = prog_name.rsplit(".", 1)[0]
    log_file_name = "{}.log".format(basename) if args.log else None
    if args.log:
        if args.verbose:
            print("Configure pywbem logger to files: requests={}, "
                  "indications={}".format('pywbem.log', log_file_name))
        configure_logger('all', log_dest='file', detail_level='all',
                         connection=True)

        if os.path.exists(log_file_name):
            if args.verbose:
                print("Removing old logfile {}".format(log_file_name))
            os.remove(log_file_name)

        logging.basicConfig(filename=log_file_name,
                            level=logging.INFO,
                            format='%(asctime)s %(levelname)s: %(message)s')

    timeout = 30
    conn = connect_wbem_server(args.wbem_server_url, args.username,
                               args.password, timeout)

    RunIndicationTest(conn, args.dest_host, args.listener_host, args.port,
                      args.indication_count, args.repeat_loop, args.verbose)

    return 0


if __name__ == '__main__':
    sys.exit(main())
