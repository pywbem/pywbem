#!/usr/bin/env python

"""
Test CIM enumerate performance with a defined class that can be controlled
from the provider TST_ResponseStressTestCxx. This is limited to OpenPegasus
because only OpenPegasus implements the defined class.
"""

from __future__ import absolute_import
import sys as _sys
import os as _os
# pylint: disable=missing-docstring,superfluous-parens,no-self-use
import datetime
# pylint: disable=unused-import
import warnings  # noqa F401
import re
import getpass as _getpass

import argparse as _argparse
from tabulate import tabulate

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from tests.utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, Error, Uint64, __version__  # noqa: E402
from pywbem._cliutils import SmartFormatter as _SmartFormatter  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# In pywbem 0.13, parse_cim() changed from a function to a method:
try:
    from pywbem._tupleparse import parse_cim
except ImportError:
    from pywbem._tupleparse import TupleParser

    def parse_cim(tt):
        """Compatible parse_cim() function"""
        tp = TupleParser()
        return tp.parse_cim(tt)

# Pegasus class/namespace to use for test
TEST_NAMESPACE = "test/TestProvider"
TEST_CLASSNAME = "TST_ResponseStressTestCxx"

# default values for the test parameters
DEFAULT_RESPONSE_SIZE = [100, 1000, 10000]
DEFAULT_RESPONSE_COUNT = [1, 100, 1000, 10000, 100000]
DEFAULT_PULL_SIZE = [1, 100, 1000]

STATS_LIST = []


def format_timedelta(td):
    """
    Return formatted time as hours:minutes:seconds.
    """
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%02d:%02d:%05.2f' % (hours, minutes, seconds)

    # return '{:02d}:{:02d}.{:05f}'.format(hours, minutes, seconds)


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
        """
        Get the elapsed time in seconds. Returns floating
        point representation of time in seconds
        """
        return self.elapsed_ms() / 1000

    def elapsed_total_sec(self):
        """
        Get the elapsed time as seconds
        """
        dt = self.elapsed_time
        # pylint: disable=no-member
        return float(dt.seconds) + (float(dt.microseconds) / 1000000)
        # pylint: enable=no-member

    def elapsed_time(self):
        """
        get the elapsed time as a time delta
        """
        return (datetime.datetime.now() - self.start_time)

    def elapsed_time_str(self):
        """
        Return elapsed time as min:sec:ms.  The .split separates out the
        milliseconds
        """
        td = (datetime.datetime.now() - self.start_time)

        sec = td.seconds
        ms = int(td.microseconds / 1000)
        return '{:02}:{:02}.{:03}'.format(sec % 3600 // 60, sec % 60, ms)

    def format_elapsed_time(self):
        """
        Return formatted time as hours:minutes:seconds.
        """
        td = self.elapsed_time()
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return '{:02}:{:02}.{:03}'.format(hours, minutes, seconds)


class _PywbemCustomFormatter(_SmartFormatter,
                             _argparse.RawDescriptionHelpFormatter):
    """
    Define a custom Formatter to allow formatting help and epilog.

    argparse formatter specifically allows multiple inheritance for the
    formatter customization and actually recommends this in a discussion
    in one of the issues:

        https://bugs.python.org/issue13023

    Also recommended in a StackOverflow discussion:

    https://stackoverflow.com/questions/18462610/argumentparser-epilog-and-description-formatting-in-conjunction-with-argumentdef
    """
    pass


def set_provider_parameters(conn, count, size):
    """Set the provider parameters with InvokeMethod"""
    try:
        result = conn.InvokeMethod("Set", TEST_CLASSNAME,
                                   [('ResponseCount', Uint64(count)),
                                    ('Size', Uint64(size))])

        if result[0] != 0:
            print('SendTestIndicationCount Method error. Nonzero return=%s'
                  % result[0])
            return False
        return True

    except Error as er:
        print('Error: Invoke Method exception %s' % er)
        raise


def record_response_times(conn, op, max_object_count, op_count, inst_count,
                          op_time):
    # pylint: disable=unused-argument
    """
    Record the server and client response times from the last response
    by appending to a list.  Appends two calculations to the result (
    difference between server time and overall response time and the
    percentage of overall response time that is not server time.)
    """
    stats = (op, max_object_count, op_count, inst_count, op_time)
    STATS_LIST.append(stats)


def run_pull_enum_instances(conn, max_object_count):
    """Execute an open request followed by pull requests"""
    op_count = 0
    et = ElapsedTimer()
    print('max_object_count %s' % max_object_count)
    result = conn.OpenEnumerateInstances(
        TEST_CLASSNAME,
        MaxObjectCount=max_object_count)
    total_op_time = et.elapsed_time()
    insts_pulled = result.instances
    record_response_times(conn, "open", max_object_count, op_count,
                          len(insts_pulled), total_op_time)

    op_count += 1
    while not result.eos:
        et.reset()
        result = conn.PullInstancesWithPath(result.context,
                                            MaxObjectCount=max_object_count)
        opelapsed_time = et.elapsed_time()
        record_response_times(conn, "pull", max_object_count, op_count,
                              len(result.instances), opelapsed_time)
        op_count += 1
        total_op_time = total_op_time + opelapsed_time
        insts_pulled.extend(result.instances)

    # return tuple containing info on the sequence (number instances pulled,
    #                                               operation ctr)
    #                                               total op time
    # The time stats are totals over the number of open/pull operations
    return (len(insts_pulled), op_count, total_op_time)


def run_single_test(conn, runid, response_count, response_size,
                    max_obj_cnt_array):
    """
    Run a single test for a defined response_count and response size and
    each entry in the max_obj_cnt variable

    Return:
        returns a list of lists (row) with result data for the enum and one row
        for each execution of the open/pull data.
    """
    rows = []

    set_provider_parameters(conn, response_count, response_size)

    # Test the time to execute EnumerateInstances()
    et = ElapsedTimer()
    instances = conn.EnumerateInstances(TEST_CLASSNAME)
    enum_time = et.elapsed_time()

    enum_count = len(instances)
    inst_per_sec = enum_count / enum_time.total_seconds()

    record_response_times(conn, "enum", 0, 0, enum_count, enum_time)
    row = ['Enum', enum_count, response_size, 0, 1,
           format_timedelta(enum_time),
           inst_per_sec, runid]
    rows.append(row)

    # Run pull test for each max_obj_cnt value
    for max_obj_cnt in max_obj_cnt_array:
        et.reset()
        result_tuple = run_pull_enum_instances(conn, max_obj_cnt)
        insts_pulled = result_tuple[0]
        pull_opcount = result_tuple[1]
        total_op_time = result_tuple[2]

        op_time = et.elapsed_time()

        inst_per_sec = insts_pulled / op_time.total_seconds()

        row = ['Open/Pull', insts_pulled, response_size, max_obj_cnt,
               pull_opcount,
               format_timedelta(total_op_time),
               inst_per_sec, runid]
        rows.append(row)
    return rows


def run_tests(conn, response_sizes, response_counts, pull_sizes,
              runid, verbose):
    """
    Run test based on limits provided defined in the input variables
    """
    test_timer = ElapsedTimer()
    # Run the enumeration one time to eliminate server startup time loss
    conn.EnumerateInstances(TEST_CLASSNAME)

    rows = []
    header = ['Operation', 'Response\nCount', 'RespSize\nBytes',
              'MaxObjCnt\nRequest',
              'operation\nCount',
              'Total execution\ntime (hh:mm:ss)',
              'inst/sec', 'runid']

    for response_size in response_sizes:
        for response_count in response_counts:
            # run_single_test(conn, response_count, response_size, pull_sizes)
            rows.extend(run_single_test(conn, runid, response_count,
                                        response_size, pull_sizes))

    print(' Response results for pywbem version %s runid %s execution time %s'
          % (__version__, runid, format_timedelta(test_timer.elapsed_time())))
    table = tabulate(rows, headers=header, tablefmt="simple")
    print(table)

    if verbose:
        rows = []
        for stat in STATS_LIST:
            rows.append(stat)
        headers = ['Operation', 'Max Object\ncount', 'Op\nCount', 'inst count',
                   'Operation\nTime']
        table = tabulate(rows, headers=headers)
        print(table)


def parse_args(prog):
    """
    Parse the input arguments and return the args dictionary
    """
    usage = '%(prog)s [options] server'
    # pylint: disable=line-too-long
    desc = """
Provide performance information on EnumerateInstances vs. Open & Pull
enumeration sequences responses.

This test runs only against the OpenPegasus server because it requires a
provider in the server that will generate responses with the number of
responses built and the size of the responses settable by a method
invoke.  In OpenPegasus, that is the 'TST_ResponseStressTestCxx' test
class and its corresponding provider.

This test uses only the WBEMConnection request methods and not the functionality
added in recent versions of pywbem (statistics, etc.) so may be executed
against any version of pywbem back to 0.10.0 and probably earlier.

Executing a test generates a table of test results defining the characteristics
of that test along with the overall time to execute and a calculation of the
number of instances per second executed.

The test output includes a column defining the pywbem version and optionally
a string runid for each test to make it easier to test multiple versions of
pywbem for performance.
"""
    epilog = """
Examples:
  %s http://blah  --response-count 10000 --pull-size 100 1000 \\
    --response-size 100 1000

  Test against server blah with the number of responses instances to a
  single request set to 10,000, the size of the maxObjectCnt request variable
  for each open and pull request set to 100 and then 1,000 and the size
  of the response objects set to first 100 and then 1000.
""" % (prog)  # noqa: E501
# pylint: enable=line-too-long

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=_PywbemCustomFormatter)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')
    pos_arggroup.add_argument(
        'server', metavar='server', nargs='?',
        help='R|Host name or url of the WBEM server in this format:\n'
             '    [{scheme}://]{host}[:{port}]\n'
             '- scheme: Defines the protocol to use;\n'
             '    - "https" for HTTPs protocol\n'
             '    - "http" for HTTP protocol.\n'
             '  Default: "https".\n'
             '- host: Defines host name as follows:\n'
             '     - short or fully qualified DNS hostname,\n'
             '     - literal IPV4 address(dotted)\n'
             '     - literal IPV6 address (RFC 3986) with zone\n'
             '       identifier extensions(RFC 6874)\n'
             '       supporting "-" or %%25 for the delimiter.\n'
             '- port: Defines the WBEM server port to be used\n'
             '  Defaults:\n'
             '     - HTTP  - 5988\n'
             '     - HTTPS - 5989\n')

    server_arggroup = argparser.add_argument_group(
        'Server related options',
        'Specify the WBEM server namespace and timeout')
    server_arggroup.add_argument(
        '-t', '--timeout', dest='timeout', metavar='timeout', type=int,
        default=None,
        help='R|Timeout of the completion of WBEM Server operation\n'
             'in seconds(integer between 0 and 300).\n'
             'Default: No timeout')

    security_arggroup = argparser.add_argument_group(
        'Connection security related options. ',
        'Specify user name and password or certificates and keys')
    security_arggroup.add_argument(
        '-u', '--user', dest='user', metavar='user',
        help='R|User name for authenticating with the WBEM server.\n'
             'Default: No user name.')
    security_arggroup.add_argument(
        '-p', '--password', dest='password', metavar='password',
        help='R|Password for authenticating with the WBEM server.\n'
             'Default: Will be prompted for, if user name\nspecified.')
    security_arggroup.add_argument(
        '-nvc', '--no-verify-cert', dest='no_verify_cert',
        action='store_true',
        help='R|Client will not verify certificate returned by the WBEM\n'
             'server (see cacerts). This bypasses the client-side\n'
             'verification of the server identity, but allows\n'
             'encrypted communication with a server for which the\n'
             'client does not have certificates.')
    security_arggroup.add_argument(
        '--cacerts', dest='ca_certs', metavar='cacerts',
        help='R|File or directory containing certificates that will be\n'
             'matched against a certificate received from the WBEM\n'
             'server. Set the --no-verify-cert option to bypass\n'
             'client verification of the WBEM server certificate.\n'
             'Default: Searches for matching certificates in the\n'
             'following system directories:\n')

    security_arggroup.add_argument(
        '--certfile', dest='cert_file', metavar='certfile',
        help='R|Client certificate file for authenticating with the\n'
             'WBEM server. If option specified the client attempts\n'
             'to execute mutual authentication.\n'
             'Default: Simple authentication.')
    security_arggroup.add_argument(
        '--keyfile', dest='key_file', metavar='keyfile',
        help='R|Client private key file for authenticating with the\n'
             'WBEM server. Not required if private key is part of the\n'
             'certfile option. Not allowed if no certfile option.\n'
             'Default: No client key file. Client private key should\n'
             'then be part  of the certfile')

    tests_arggroup = argparser.add_argument_group(
        'Test related options',
        'Specify parameters of the test')

    tests_arggroup.add_argument(
        '--response-count', dest='response_count', nargs='+',
        metavar='int', type=int,
        action='store', default=DEFAULT_RESPONSE_COUNT,
        help='R|The number of instances that will be returned for each test\n'
             'in the form for each test. May be multiple integers. The test\n'
             'will be executed for each integer defined. The format is:\n'
             '  --response-count 1000 10000 100000\n'
             'Default: %s' % DEFAULT_RESPONSE_COUNT)

    tests_arggroup.add_argument(
        '--pull-size', dest='pull_size', nargs='+',
        metavar='int', type=int,
        action='store', default=DEFAULT_PULL_SIZE,
        help='R|The maxObjectCount defined for each pull operation that will\n'
             'be tested. This defines the MaxObjectCount for each open and \n'
             'pull request for each test. May be multiple integers. The test\n'
             'will be executed for each integer defined. The format is:\n'
             '  --pull-size 100 200 300\n'
             'Default: %s' % DEFAULT_PULL_SIZE)

    tests_arggroup.add_argument(
        '--response-size', dest='response_size', nargs='+',
        metavar='int', type=int,
        action='store', default=DEFAULT_RESPONSE_SIZE,
        help='R|The response sizes that will be tested. This defines the size\n'
             'of each response in bytes to be returned from the server.\n'
             'May be multiple integers. The test will be executed for each\n'
             'integer defined. The format is:\n'
             '  --response-size 100 200 300\n'
             'Default: %s' % DEFAULT_RESPONSE_SIZE)

    tests_arggroup.add_argument(
        '-r', '--runid', dest='runid',
        metavar='text', type=str,
        action='store', default=None,
        help='R|A Optional string that is included in the output report to \n'
             'identify this test run. It is concatenated with the pywbem\n'
             'version.\n'
             'Default: %s' % None)

    general_arggroup = argparser.add_argument_group(
        'General options')

    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='R|Print more messages while processing. Displays detailed\n'
             'counts for each pull operation.')
    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    args = argparser.parse_args()

    if not args.server:
        argparser.error('No WBEM server specified')

    if args.server[0] == '/':
        url = args.server

    elif re.match(r"^https{0,1}://", args.server) is not None:
        url = args.server

    elif re.match(r"^[a-zA-Z0-9]+://", args.server) is not None:
        argparser.error('Invalid scheme on server argument.'
                        ' Use "http" or "https"')

    else:
        url = '%s://%s' % ('https', args.server)

    if args.key_file is not None and args.cert_file is None:
        argparser.error('keyfile option requires certfile option')

    return args, url


def main(prog):
    """
    Parse command line arguments, connect to the WBEM server and open the
    interactive shell.
    """
    args, url = parse_args(prog)

    creds = None

    if args.user is not None and args.password is None:
        args.password = _getpass.getpass('Enter password for %s: '
                                         % args.user)

    if args.user is not None or args.password is not None:
        creds = (args.user, args.password)

    # if client cert and key provided, create dictionary for
    # wbem connection
    x509_dict = None
    if args.cert_file is not None:
        x509_dict = {"cert_file": args.cert_file}
        if args.key_file is not None:
            x509_dict.update({'key_file': args.key_file})

    conn = WBEMConnection(url, creds, default_namespace=TEST_NAMESPACE,
                          no_verification=True,
                          x509=x509_dict, ca_certs=args.ca_certs,
                          timeout=args.timeout)

    print('Test with response sizes=%s response_counts=%s, pull_sizes=%s\n' %
          (args.response_size, args.response_count, args.pull_size))

    if args.runid:
        runid = "%s:%s" % (__version__, args.runid)
    else:
        runid = __version__

    run_tests(conn, args.response_size, args.response_count, args.pull_size,
              runid, args.verbose)

    return 0


if __name__ == '__main__':
    _sys.exit(main(_os.path.basename(_sys.argv[0])))
