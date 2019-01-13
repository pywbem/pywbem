#!/usr/bin/env python

"""
Test CIM enumerate performance with a defined class that can be controlled
from the provider TST_ResponseStressTestCxx. This is limited to OpenPegasus
because only OpenPegasus implements the defined class.
"""

from __future__ import absolute_import
import sys as _sys
# pylint: disable=missing-docstring,superfluous-parens,no-self-use
import datetime
# pylint: disable=unused-import
import warnings  # noqa F401

import argparse as _argparse
from argparse import RawTextHelpFormatter

import getpass as _getpass
import re

from pywbem import WBEMConnection, Error, Uint64

# Pegasus class/namespace to use for test
TEST_NAMESPACE = "test/TestProvider"
TEST_CLASSNAME = "TST_ResponseStressTestCxx"

TABLE_FORMAT = '%-10.10s %-10.10s %-10.10s %-10.10s %-10.10s %-11.11s %-10.10s'


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


def run_enum_instances(conn):
    """Execute an EnumerateInstances request and return the instances"""
    instances = conn.EnumerateInstances(TEST_CLASSNAME)
    return len(instances)


def run_pull_enum_instances(conn, max_object_count):
    """Execute an open request followed by pull requests"""
    op_count = 0
    result = conn.OpenEnumerateInstances(
        TEST_CLASSNAME,
        MaxObjectCount=max_object_count)
    insts_pulled = result.instances

    op_count += 1

    while not result.eos:
        result = conn.PullInstancesWithPath(result.context,
                                            MaxObjectCount=max_object_count)
        op_count += 1
        insts_pulled.extend(result.instances)

    # return tuple containing info on the sequence
    return [len(insts_pulled), op_count]


def run_single_test(conn, response_count, response_size, max_obj_cnt_array):
    """run a single test for a defined response_count and response size"""

    set_provider_parameters(conn, response_count, response_size)

    start_time = datetime.datetime.now()
    enum_count = run_enum_instances(conn)
    enum_time = datetime.datetime.now() - start_time
    inst_per_sec = '%06.2f' % (enum_count / enum_time.total_seconds())
    print(TABLE_FORMAT % ('Enum', enum_count, response_size,
                          'na', 'na', enum_time, inst_per_sec))

    for max_obj_cnt in max_obj_cnt_array:
        pull_start_time = datetime.datetime.now()
        pull_result = run_pull_enum_instances(conn, max_obj_cnt)
        pull_time = datetime.datetime.now() - pull_start_time
        inst_per_sec = '%06.2f' % (pull_result[0] / pull_time.total_seconds())

        print(TABLE_FORMAT % ('Open/Pull', pull_result[0], response_size,
                              max_obj_cnt, pull_result[1], pull_time,
                              inst_per_sec))


def run_tests(conn):
    """Run test based on limits provided"""

    print(TABLE_FORMAT % ('Operation', 'Response', 'RespSize', 'MaxObjCnt',
                          'Request', 'Time', 'inst/sec'))
    print(TABLE_FORMAT % ('', 'Count', 'Bytes', 'Request',
                          'Count', '', ''))
    for response_size in [100, 1000, 10000]:
        for response_count in [1, 100, 1000, 10000, 100000]:
            pull_sizes = [1, 100, 1000]
            run_single_test(conn, response_count, response_size, pull_sizes)


def main(prog):
    """
    Parse command line arguments, connect to the WBEM server and open the
    interactive shell.
    """

    usage = '%(prog)s [options] server'
    desc = """
Provide performance information on EnumerateInstances vs. Open & Pull
enumeration sequences responses.

Generates a table of response times for an array of max_object_count,
response sizes, etc.values.
"""
    epilog = """
Examples:
  %s https://localhost:15345 -n vendor -u sheldon -p penny
          - (https localhost, port=15345, namespace=vendor user=sheldon
         password=penny)

  %s http://[2001:db8::1234-eth0] -(http port 5988 ipv6, zone id eth0)
""" % (prog, prog)

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=RawTextHelpFormatter)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')
    pos_arggroup.add_argument(
        'server', metavar='server', nargs='?',
        help='Host name or url of the WBEM server in this format:\n'
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
        help='Timeout of the completion of WBEM Server operation\n'
             'in seconds(integer between 0 and 300).\n'
             'Default: No timeout')

    security_arggroup = argparser.add_argument_group(
        'Connection security related options',
        'Specify user name and password or certificates and keys')
    security_arggroup.add_argument(
        '-u', '--user', dest='user', metavar='user',
        help='User name for authenticating with the WBEM server.\n'
             'Default: No user name.')
    security_arggroup.add_argument(
        '-p', '--password', dest='password', metavar='password',
        help='Password for authenticating with the WBEM server.\n'
             'Default: Will be prompted for, if user name\nspecified.')
    security_arggroup.add_argument(
        '-nvc', '--no-verify-cert', dest='no_verify_cert',
        action='store_true',
        help='Client will not verify certificate returned by the WBEM\n'
             'server (see cacerts). This bypasses the client-side\n'
             'verification of the server identity, but allows\n'
             'encrypted communication with a server for which the\n'
             'client does not have certificates.')
    security_arggroup.add_argument(
        '--cacerts', dest='ca_certs', metavar='cacerts',
        help='File or directory containing certificates that will be\n'
             'matched against a certificate received from the WBEM\n'
             'server. Set the --no-verify-cert option to bypass\n'
             'client verification of the WBEM server certificate.\n'
             'Default: Searches for matching certificates in the\n'
             'following system directories:\n')

    security_arggroup.add_argument(
        '--certfile', dest='cert_file', metavar='certfile',
        help='Client certificate file for authenticating with the\n'
             'WBEM server. If option specified the client attempts\n'
             'to execute mutual authentication.\n'
             'Default: Simple authentication.')
    security_arggroup.add_argument(
        '--keyfile', dest='key_file', metavar='keyfile',
        help='Client private key file for authenticating with the\n'
             'WBEM server. Not required if private key is part of the\n'
             'certfile option. Not allowed if no certfile option.\n'
             'Default: No client key file. Client private key should\n'
             'then be part  of the certfile')

    general_arggroup = argparser.add_argument_group(
        'General options')
    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Print more messages while processing')
    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    opts = argparser.parse_args()

    if not opts.server:
        argparser.error('No WBEM server specified')

    if opts.server[0] == '/':
        url = opts.server

    elif re.match(r"^https{0,1}://", opts.server) is not None:
        url = opts.server

    elif re.match(r"^[a-zA-Z0-9]+://", opts.server) is not None:
        argparser.error('Invalid scheme on server argument.'
                        ' Use "http" or "https"')

    else:
        url = '%s://%s' % ('https', opts.server)

    creds = None

    if opts.key_file is not None and opts.cert_file is None:
        argparser.error('keyfile option requires certfile option')

    if opts.user is not None and opts.password is None:
        opts.password = _getpass.getpass('Enter password for %s: '
                                         % opts.user)

    if opts.user is not None or opts.password is not None:
        creds = (opts.user, opts.password)

    # if client cert and key provided, create dictionary for
    # wbem connection
    x509_dict = None
    if opts.cert_file is not None:
        x509_dict = {"cert_file": opts.cert_file}
        if opts.key_file is not None:
            x509_dict.update({'key_file': opts.key_file})

    conn = WBEMConnection(url, creds, default_namespace=TEST_NAMESPACE,
                          no_verification=True,
                          x509=x509_dict, ca_certs=opts.ca_certs,
                          timeout=opts.timeout)

    run_tests(conn)

    return 0


if __name__ == '__main__':
    _sys.exit(main('run_enum_performance.py'))
