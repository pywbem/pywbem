"""
End2end tests of indications from a wbem server. This tests:
1. creating the subscription in the container
2. Creating the pywbemlistener
3. Receiving indications from the server. It uses only OpenPegasus WBEM server
because OpenPegasus defines a provider in its test environment specifically to
send indications based on a method invocation and we have a container
implementation of OpenPegasus.

"""

from __future__ import absolute_import, print_function

import socket
import time
import sys
import os
import datetime
import logging

from pytest import skip

from .utils.pytest_extensions import skip_if_unsupported_capability

# Note: The wbem_connection fixture uses the es_server fixture, and
# due to the way py.test searches for fixtures, it also must be imported.
# pylint: disable=unused-import,wrong-import-order, relative-beyond-top-level
from .utils.pytest_extensions import wbem_connection  # noqa: F401
from pytest_easy_server import es_server  # noqa: F401
from .utils.pytest_extensions import default_namespace  # noqa: F401
# pylint: enable=unused-import,wrong-import-order, relative-beyond-top-level

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
# pylint: disable=relative-beyond-top-level, disable=redefined-builtin
from ..utils import import_installed

pywbem = import_installed('pywbem')
from pywbem import WBEMServer, WBEMListener, CIMClassName, \
    Error, Uint32, WBEMSubscriptionManager, \
    configure_logger  # noqa: E402
# pylint: enable=relative-beyond-top-level, enable=redefined-buitin
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def test_indications(wbem_connection):  # pylint: disable=redefined-outer-name
    """
    Test indication subscription to a container and reception of indications
    from the container.
    """
    skip_if_unsupported_capability(wbem_connection, 'interop')

    # Get a real IP address for the machine to insert into  the
    # indication_destination_host variable. This must be an address available
    # to both the test machine/vm/etc. and the container in which OpenPegasus
    # is running so OpenPegasus can route indications to the listener.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    indication_dest_host = s.getsockname()[0]

    # Use the empty string host that allows receving indications addressed to
    # any valid valid destination on the system.
    listener_host = ""
    port = 5000
    log = True
    verbose = True

    # define repeat_loop and indication_count variables to rerun the test with
    # each of these pairs. (repeat_loop, indication_count)
    # FUTURE: Expand this to more indications when we resolve issue #3022,
    # the container not returning all of the indications.  This appears to
    # be much more consistent with python 3.7 and 3.7 PACKAGE_LEVEL=minimum

    if sys.version_info[0:2] in ((2, 7), (3, 7)):
        skip("Skipping test_indications for python 2.7")
    else:
        test_run_loops = ((1, 2), (1, 10), )

    for params in test_run_loops:
        repeat_loop = params[0]
        indication_count = params[1]

        RunIndicationTest(wbem_connection, indication_dest_host, listener_host,
                          port, indication_count, repeat_loop, log,
                          verbose=verbose)


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

    def __init__(self, wbem_conn, indication_destination_host,
                 listener_host, http_listener_port, requested_indications,
                 repeat_loop, output_log, verbose):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-arguments
        """
        Sets up and runs the indication test and removes subscriptions at the
        completion of the test.  There no return from this instance, it
        closes with the test complete or with an exception if the setup
        or test fails.

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
                host name/ip address that will be used by the listener as
                its bind address. If this parameter contains
                a string that will be passed to WBEMListener as the host
                parameter. That name/IP address is used by the the socket
                services to only accept indications addressed to that
                network interface or IP address (depening on the OS, network,
                etc.)
                If None the listener will be forwarded indications addressed
                to any IP address in the containing computer system.

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

            output_log (:class:`py:bool`):
                Flag to indicate whether the server should generate a log.

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
        self.logfile = 'pegasusindicationtest.log'
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
            if self.verbose:
                print("Removed existing subscriptions")

        except Error as er:  # pylint: disable=invalid-name
            print('Error {} communicating with WBEMServer {}'.format(er,
                                                                     self.conn))
            assert False

        self.create_listener()

        self.create_subscription(self.server_id, sub_mgr)

        # Run the test the number of times defined by repeat_loop
        success = self.repeat_test_loop(self.repeat_loop)

        completion_status = "Success" if success else "Failed"
        print("Indication test completed: {}".format(completion_status))

        # Remove server_id which removes owned subscriptions for this server_id
        sub_mgr.remove_server(self.server_id)

        self.listener.stop()

        assert success

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
                    print("Full instnace of OpenPegasus dest queue:\n{}".
                          format(inst.tomof()))
        return success

    def get_elapsed_time(self):
        """
        Compute elapsed time and indications per second

        returns elapsed time in seconds and count of indications per second
        """
        # If indications received
        if self.received_indication_count != self.requested_indications:
            elapsed_time = \
                self.last_indication_time - self.indication_start_time
            elapsed_time = elapsed_time.total_seconds()
            ind_per_sec = self.received_indication_count / \
                elapsed_time if elapsed_time else 0
        else:
            elapsed_time = 0
            ind_per_sec = 0

        return elapsed_time, ind_per_sec

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
                # Note that this allows for more than expected . There is
                # an error message further down in the code
                if self.received_indication_count >= self.requested_indications:
                    elapsed_time, ind_per_sec = self.get_elapsed_time()

                    print('Rcvd {} indications, time={} sec, {:.2f} per sec'
                          .format(self.received_indication_count,
                                  elapsed_time,
                                  ind_per_sec))
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
                else:
                    stalled_time = datetime.datetime.now() - \
                        self.indication_start_time

                if stall_ctr > 5:
                    elapsed_time, ind_per_sec = self.get_elapsed_time()

                    print('Nothing received for {} sec: received={} '
                          'time={} sec: {:.2f} per sec. stall ctr={}'.
                          format(stalled_time.total_seconds(),
                                 self.received_indication_count,
                                 elapsed_time,
                                 ind_per_sec,
                                 stall_ctr))
                    break

                print("waiting {:.2f} sec. with no indications ct {}".
                      format(stalled_time.total_seconds(), stall_ctr))

        # Because this can be a long loop, catch CTRL-C
        except KeyboardInterrupt:
            print('Ctrl-C terminating wait loop early')

        # If return_flag True, wait and recheck to be sure no extras
        # received.
        if return_flag:
            time.sleep(1)
            if self.received_indication_count != self.requested_indications:
                print('ERROR. Extra indications received {}, requested {}'.
                      format(self.received_indication_count,
                             self.requested_indications))
            if return_flag:
                assert self.received_indication_count == \
                    self.requested_indications
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
