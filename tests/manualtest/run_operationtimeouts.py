#!/usr/bin/env python

"""
Test CIM operations against a real WBEM server that is specified on the
command line.  It executes a specific test to test for correct operation of
the WBEMConnection timeout option in multiple modes of the server and client.
Specifically it tests both http and https schemes and confirms that the
timeout exception is received correctly over a wide range of timeout values.

Note that this test uses a specific class and method in OpenPegasus today to
execute an operation with a specified delay.

The default for this test takes several minutes to run because of size of
the maximum timeout (20 seconds)
"""


# pylint: disable=missing-docstring,superfluous-parens,no-self-use
import sys
import unittest
import warnings
import datetime
from getpass import getpass

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from tests.utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, Uint32, ConnectionError, \
    TimeoutError  # noqa: E402 pylint: disable=redefined-builtin
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Identity of the OpenPegasus namespace, class, and method that implements
# the delayed response. NOTE: This is only available on OpenPegasus 2.15+.
NAMESPACE = 'test/testprovider'
TESTCLASS = 'Test_CLITestProviderClass'
TESTMETHOD = 'delayedMethodResponse'


class ElapsedTimer:
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
        return ((dt.days * 24 * 3600) + dt.seconds) * 1000 + \
            dt.microseconds / 1000.0

    def elapsed_sec(self):
        """ get the elapsed time in seconds. Returns floating
            point representation of time in seconds
        """
        return self.elapsed_ms() / 1000


class ClientTest(unittest.TestCase):
    """ Base class that creates a pywbem.WBEMConnection for
        subclasses to use based on cmd line arguments. It provides
        a common cimcall method that executes test calls and logs
        results
    """

    def setUp(self):
        """Create a connection."""

        # pylint: disable=global-variable-not-assigned,global-statement
        global args  # noqa: F824 pylint: disable=invalid-name

        # pylint: disable=used-before-assignment
        # pylint: disable=possibly-used-before-assignment
        self.host = args['host']
        self.port = args['port']
        self.verbose = args['verbose']
        self.debug = args['debug']
        self.maxtimeout = args['maxtimeout']
        self.mintimeout = 2
        self.stop_on_err = args['stopOnErr']

        # set this because python 3 http libs generate many ResourceWarnings
        # and unittest enables these warnings.
        # pylint: disable=undefined-variable
        warnings.simplefilter("ignore", ResourceWarning)  # noqa: F821

    def connect(self, url, timeout=None):

        self.log(f'setup connection {url} timeout {timeout}')
        conn = WBEMConnection(
            url,
            (args['username'], args['password']),
            NAMESPACE,
            timeout=timeout,
            no_verification=True,
            ca_certs=None)

        # enable saving xml for display
        conn.debug = args['debug']
        self.log(f'Connected {url}')
        return conn

    def log(self, data_):
        """Display log entry if verbose"""
        if self.debug:
            print(f'{data_}')


class ServerTimeoutTest(ClientTest):

    def execute(self, url, timeout, delay):
        """
            Execute a single connect with timeout, followed by invokemethod
            of the method that delays response and test for possible responses.

            Tests for correct response type (good response if the delay is
            less than the timeout and timeout exception if the delay is greater
            than the timeout.  It ignores results where the operation delay
            and timeout are equal since the result could be either timeout
            or good response.
        """
        conn = self.connect(url, timeout=timeout)
        execution_time = None

        if self.debug:
            print(f'execute url_type={url} timeout={timeout} delay={delay}')

        err_flag = ""
        opttimer = ElapsedTimer()
        try:
            # Confirm server working with a simple request.
            conn.GetClass('CIM_ManagedElement')
            request_result = 0     # good response
            conn.InvokeMethod(TESTMETHOD, TESTCLASS,
                              [('delayInSeconds', Uint32(delay))])

            execution_time = opttimer.elapsed_sec()

            if delay > timeout:
                err_flag = "Timeout Error: delay gt timeout"
                if self.stop_on_err:
                    self.fail('should not get good response for '
                              f'{delay} > {timeout}')
            if delay == timeout:
                err_flag = "Good when timeout matches delay"

        # This exception terminates the test
        except ConnectionError as ce:
            request_result = 2    # Connection error received
            err_flag = "ConnectionError"
            execution_time = opttimer.elapsed_sec()

            self.fail(f'Failed(ConnectionError) exception {ce}')

        # this exception tests against expected result. It terminates the
        # test only if the timeout is not expected
        except TimeoutError:
            execution_time = opttimer.elapsed_sec()
            err_flag = "TimeoutError Xcpt"
            execution_time = opttimer.elapsed_sec()
            request_result = 1    # timeout error received
            # error if the operation delay is lt timeout value and we get
            # a timeout
            if delay < timeout:
                err_flag = 'Error. delay < timeout'
                if self.stop_on_err:
                    self.fail(f'should not get timeout for {delay} < {timeout}')
            if delay == timeout:
                err_flag = "Timeout when timeout matches delay"

        # This exception terminates the test if stop_on_err set.
        except Exception as ec:      # pylint: disable=broad-except
            err_flag = "Test Failed.General Exception"
            execution_time = opttimer.elapsed_sec()
            request_result = 2
            if self.stop_on_err:
                self.fail(f'Failed(Exception) exception {ec}')

        # generate table entry if verbose. This defines result for this
        # test
        if self.verbose:
            request_result_txt = ['Good Rtn', 'Timeout ', 'Failure']

            print(f'{url:-12s} {request_result_txt[request_result]:-7s} '
                  f'{timeout:7d} {delay:5d} {execution_time:10.2f}  {err_flag}')

        return (request_result == 1)

    def test_all(self):
        """ Tests all of the variations in a loop."""

        print('url   result   timeout delay  time(sec)  Comments')

        for url_type in ['https', 'http']:
            if self.port:
                if url_type == 'http':
                    port = f":{self.port}"
                else:
                    port = f":{self.port + 1}"
            else:
                port = ""

            url = url_type + '://' + self.host + port

            for timeout in range(self.mintimeout, self.maxtimeout):

                # loop while good response received to test range of
                # server delays. Test for range around current timeout value
                break_loop = False
                min_delay = timeout - 2
                max_delay = timeout * 3
                good_rtn_rcvd = False
                timeout_rcvd = False
                for delay in range(min_delay, max_delay):
                    timed_out = self.execute(url, timeout, delay)
                    if not timed_out:
                        good_rtn_rcvd = True
                    if timed_out:
                        timeout_rcvd = True

                    # After return indicates timeout, run one more test
                    # then break delay loop. Assures that the timeour
                    # response is consistent.
                    if break_loop:
                        break
                    if timed_out:
                        break_loop = True
                # confirm that both a good response and timeout received for
                # this delay range.
                self.assertTrue(timeout_rcvd, "Timeout never received")
                self.assertTrue(good_rtn_rcvd, "Good return never received")


def parse_args(argv_):
    argv = list(argv_)

    if len(argv) <= 1:
        print('Error: No arguments specified; Call with --help or -h for '
              'usage.')
        sys.exit(2)
    elif argv[1] == '--help' or argv[1] == '-h':
        print('')
        print('Test program for client timeout of cim operations.\n')
        print('Requires OpenPegasus because it uses a special method\n')
        print('that delays the response for a defined time.\n')
        print('Tests a range of timeout values against http\n ')
        print('and https with operation that generates known delay.\n')
        print('Complete test is in a single unittest function')
        print('')
        print('Usage:')
        print(f'    {argv[0]} [GEN_OPTS] URL [USERNAME%%PASSWORD [UT_OPTS '
              '[UT_CLASS ...]]] ')
        print('')
        print('Where:')
        print('    GEN_OPTS            General options (see below).')
        print('    HOST                Name of the target WBEM server.\n'
              '                        No Scheme prefix\n'
              '                        defines ssl usage')
        print('    USERNAME            Userid used to log into\n'
              '                        WBEM server.\n'
              '                        Requests user input if not supplied')
        print('    PASSWORD            Password used to log into\n'
              '                        WBEM server.\n'
              '                        Requests user input if not supplier')

        print('')
        print('General options[GEN_OPTS]:')
        print('    --help, -h          Display this help text.')
        print('    -t MAXTIMEOUT       Maximum timout value in sec. to test.\n'
              '                        default is 20 sec.')
        print('    -v                  Verbose output which includes\n'
              '                        result of each test.')
        print('    -s                  Stop test on first timeout error.\n'
              '                        Otherwise errors in timeout are just\n'
              '                        reported. Other errors stop test.')
        print('    -d                  Debug flag for extra displays')
        print('    -p                  Port for http. If not provided, uses')
        print('                        DMTF default port of 5988')
        print('------------------------')
        print('Unittest arguments[UT_OPTS]:')
        print('')
        sys.argv[1:] = ['--help']
        unittest.main()
        sys.exit(2)

    args_ = {}
    # set argument defaults
    args_['maxtimeout'] = 20
    args_['stopOnErr'] = False
    args_['verbose'] = False
    args_['username'] = None
    args_['password'] = None
    args_['debug'] = False
    args_['port'] = None

    # options must proceed arguments
    while True:
        if argv[1][0] != '-':
            # Stop at first non-option
            break

        if argv[1] == '-t':
            args_['maxtimeout'] = int(argv[2])
            del argv[1:3]
        elif argv[1] == '-d':
            args_['delay'] = int(argv[2])
            del argv[1:3]
        elif argv[1] == '-p':
            args_['port'] = int(argv[2])
            del argv[1:3]
        elif argv[1] == '-v':
            args_['verbose'] = True
            del argv[1:2]
        elif argv[1] == '-d':
            args_['debug'] = True
            del argv[1:2]
        elif argv[1] == '-s':
            args_['stopOnErr'] = True
            del argv[1:2]
        elif argv[1] == '-d':
            args_['debug'] = True
            del argv[1:2]
        else:
            print(f"Error: Unknown option: {argv[1]}")
            sys.exit(1)

    args_['host'] = argv[1]
    del argv[1:2]

    if len(argv) >= 2:
        args_['username'], args_['password'] = argv[1].split('%')
        del argv[1:2]
    else:
        # Get user name and pw from console
        sys.stdout.write('Username: ')
        sys.stdout.flush()
        args_['username'] = sys.stdin.readline().strip()
        args_['password'] = getpass()
    return args_, argv


if __name__ == '__main__':
    args, sys.argv = parse_args(sys.argv)  # pylint: disable=invalid-name

    if args['verbose'] in args:
        print("Using WBEM Server:")
        print(f"  host: {args['host']}")
        print(f"  username: {args['username']}")
        if args['password'] is not None:
            print("  password: {}".format("*" * len(args['password'])))
        print(f"  maxtimeout: {args['maxtimeout']}")
        print(f"  verbose: {args['verbose']}")
        print(f"  stopOnErr: {args['stopOnErr']}")
        print(f"  debug: {args['debug']}")
        print(f"  port: {args['port']}")

    # Note: unittest options are defined in separate args after
    # the url argument.

    unittest.main()
