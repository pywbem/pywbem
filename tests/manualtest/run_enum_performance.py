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
from pywbem import WBEMConnection, Error, Uint64, \
    TestClientRecorder  # noqa: E402
from pywbem._cliutils import SmartFormatter as _SmartFormatter  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Pegasus class/namespace to use for test
TEST_NAMESPACE = "test/TestProvider"
TEST_CLASSNAME = "TST_ResponseStressTestCxx"

# default values for the test parameters
DEFAULT_RESPONSE_SIZE = [100, 1000, 10000]
DEFAULT_RESPONSE_COUNT = [1, 100, 1000, 10000, 100000]
DEFAULT_PULL_SIZE = [1, 100, 1000]


STATS_LIST = []


def format_timedelta(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%02d:%02d:%05.2f' % (hours, minutes, seconds)


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


def record_response_times(conn, max_object_count, op_count):
    """
    Record the server and client response times from the last response
    by appending to a list.  Appends two calculations to the result (
    difference between server time and overall response time and the
    percentage of overall response time that is not server time.)
    """
    stats = (max_object_count, op_count, conn.last_server_response_time,
             conn.last_operation_time)
    STATS_LIST.append(stats)


def run_pull_enum_instances(conn, max_object_count):
    """Execute an open request followed by pull requests"""
    op_count = 0
    result = conn.OpenEnumerateInstances(
        TEST_CLASSNAME,
        MaxObjectCount=max_object_count)
    insts_pulled = result.instances
    record_response_times(conn, max_object_count, op_count)

    op_count += 1

    total_svr_response_time = 0
    total_op_time = 0

    while not result.eos:
        result = conn.PullInstancesWithPath(result.context,
                                            MaxObjectCount=max_object_count)
        record_response_times(conn, max_object_count, op_count)
        op_count += 1
        insts_pulled.extend(result.instances)
        total_op_time = 0
        if conn.last_server_response_time:
            total_svr_response_time += conn.last_server_response_time
        else:
            total_svr_response_time = 0
        total_op_time += conn.last_operation_time

    # return tuple containing info on the sequence (instances pulled,
    #                                               zero origin opertion ctr)
    #                                               tuple of time stats
    # The time stats are totals over the number of open/pull operations
    return [len(insts_pulled), op_count,
            (total_svr_response_time,   # 0
             total_op_time)]            # 1


def run_single_test(conn, response_count, response_size, max_obj_cnt_array):
    """
    Run a single test for a defined response_count and response size
    """
    rows = []

    set_provider_parameters(conn, response_count, response_size)

    # Test the time to execute EnumerateInstances()
    start_time = datetime.datetime.now()
    instances = conn.EnumerateInstances(TEST_CLASSNAME)
    enum_count = len(instances)
    enum_time = datetime.datetime.now() - start_time
    inst_per_sec = enum_count / enum_time.total_seconds()

    # if server returned a value for the last server response time
    # use that to compute the difference between the total and server time.
    if conn.last_server_response_time:
        diff = conn.last_operation_time - conn.last_server_response_time
    else:
        diff = conn.last_operation_time

    client_pulltime_str = format_timedelta(enum_time)
    percentage = "{:0.2f}".format((diff / conn.last_operation_time) * 100)

    row = ['Enum', enum_count, response_size, None, None,
           client_pulltime_str,
           inst_per_sec,
           conn.last_server_response_time,
           conn.last_operation_time,
           diff,
           percentage]
    rows.append(row)

    # Run pull test for each requests max_obj_cnt
    for max_obj_cnt in max_obj_cnt_array:
        pull_start_time = datetime.datetime.now()
        insts_pulled, pull_opcount, pull_stats = run_pull_enum_instances(
            conn, max_obj_cnt)
        client_pull_time = datetime.datetime.now() - pull_start_time

        client_pulltime_str = format_timedelta(client_pull_time)
        total_server_responsetime = pull_stats[0]
        total_operationtime = pull_stats[1]

        inst_per_sec = insts_pulled / client_pull_time.total_seconds()

        pywbem_processingtime = total_operationtime - total_server_responsetime

        # total_operationtime exists only if the server returns it
        if total_operationtime:
            percentage = "{:0.2f}".format((pywbem_processingtime /
                                           conn.last_operation_time) * 100)
        else:
            percentage = 100  # This is fake but we don't know svr time.

        row = ['Open/Pull', insts_pulled, response_size, max_obj_cnt,
               pull_opcount,
               client_pulltime_str,
               inst_per_sec,
               total_server_responsetime,
               total_operationtime,
               diff,
               percentage]
        rows.append(row)
    return rows


def run_tests(conn, response_sizes, response_counts, pull_sizes, verbose):
    """
    Run test based on limits provided defined in the input variables
    """
    # Run the enumeration one time to eliminate server startup time loss
    conn.EnumerateInstances(TEST_CLASSNAME)

    if conn.last_server_response_time is None:
        print('WARNING: Server probably not returning server response time')

    rows = []
    header = ['Operation', 'Response\nCount', 'RespSize\nBytes',
              'MaxObjCnt\nRequest',
              'Result\nCount',
              'Total execution\ntime (hh:mm:ss)',
              'inst/sec',
              'svr time\nsec',
              'operation\nresp time\nsec',
              'totalop - svr\nresp time\nsec',
              'totalop - svr\nresp time\npercent']

    for response_size in response_sizes:
        for response_count in response_counts:
            # run_single_test(conn, response_count, response_size, pull_sizes)
            rows.extend(run_single_test(conn, response_count, response_size,
                                        pull_sizes))

    table = tabulate(rows, headers=header, tablefmt="simple")
    print(table)

    if verbose:
        print('\n\n')
        print(conn.statistics.formatted())
        print("\n\nIndividual Returns for response-counts=%s" % response_counts)
        headers = ('ObjsCnt', 'Pull#', 'SvrTime', 'RspTime',
                   'OpTime-SvrTime', '%Not Svr')

        print("{0:6s} {1:5s} {2:7s} {3:7s} {4:14s} {5:10s}".
              format(*headers))

        print('\n\nDetailed statistics for each pull  operations')
        for st in STATS_LIST:
            diff = conn.last_operation_time - conn.last_server_response_time
            percentage = (diff / conn.last_operation_time) * 100
            print(
                '{0:6d} {1:5d} {2:7.3f} {3:7.3f} {4:14.3f} {5:7.1f}%'
                .format(st[0], st[1], st[2], st[3], diff, percentage))


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

Further, this test uses the capability of the server to return information
on the server response time as part of the response. This capability is
included in the OpenPegasus server and is enabled by setting a property
`GatherStatisticalData` in the `CIM_ObjectManager`.

Executing a test generates several tables of response times for the various
test parameters
"""
    epilog = """
Examples:
  %s http://blah --response-count 10000 --pull-size 100 1000 \\
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
        help='R|The maxObjectCount defined for each pull operation  that will\n'
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

    general_arggroup = argparser.add_argument_group(
        'General options')

    general_arggroup.add_argument(
        '--record', dest='record', type=str,
        default=None,
        help='R|Create a yaml output file recording the test in the filename\n'
             'defined by the string. If this parameter not provided no\n'
             'output file is created.')

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
                          timeout=args.timeout,
                          stats_enabled=True)

    if args.record is not None:
        yamlfp = TestClientRecorder.open_file(args.record, 'a')
        conn.add_operation_recorder(TestClientRecorder(yamlfp))

    print('Test with response sizes=%s response_counts=%s, pull_sizes=%s\n' %
          (args.response_size, args.response_count, args.pull_size))

    run_tests(conn, args.response_size, args.response_count, args.pull_size,
              args.verbose)

    return 0


if __name__ == '__main__':
    _sys.exit(main(_os.path.basename(_sys.argv[0])))
