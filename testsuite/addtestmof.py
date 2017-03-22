#!/usr/bin/env python
#
from __future__ import print_function, absolute_import

import sys as _sys
import os as _os
import getpass as _getpass
import re
import argparse as _argparse
from pywbem import WBEMConnection, CIMError
from pywbem.mof_compiler import MOFCompiler
from pywbem.cim_http import get_default_ca_cert_paths
from pywbem._cliutils import SmartFormatter as _SmartFormatter

LOGFILE = None
SCRIPT_DIR = None


def moflog(msg):
    """Display message to moflog"""
    print(msg, file=LOGFILE)


def compile_mof(conn, mof_file, namespace):
    """Compile the mof_file into the server defined by conn"""

    moflog_file = _os.path.join(SCRIPT_DIR, 'addtestnif.txt')
    global LOGFILE
    LOGFILE = open(moflog_file, 'w')
    mofcomp = MOFCompiler(
        conn,
        search_paths=[SCRIPT_DIR],
        verbose=False,
        log_func=moflog)
    mofcomp.compile_file(mof_file, namespace)


def test_compiled_mof(conn):
    """Test the compiled mof by access in connected server."""

    conn.GetClass('PyWBEM_Person')
    conn.GetClass('PyWBEM_PersonCollection')
    conn.GetClass('PyWBEM_MemberOfPersonCollection')
    inst_names = conn.EnumerateInstanceNames('PyWBEM_Person')
    assert(len(inst_names) == 3)

    assoc_names = conn.AssociatorNames(inst_names[0])
    assert(len(assoc_names) == 1)


def _remote_connection(server, opts, argparser_):
    """Initiate a remote connection, via PyWBEM. Arguments for
       the request are part of the command line arguments and include
       user name, password, namespace, etc.
    """

    if server[0] == '/':
        url = server

    elif re.match(r"^https{0,1}://", server) is not None:
        url = server

    elif re.match(r"^[a-zA-Z0-9]+://", server) is not None:
        argparser_.error('Invalid scheme on server argument.'
                         ' Use "http" or "https"')

    else:
        url = '%s://%s' % ('https', server)

    creds = None

    if opts.key_file is not None and opts.cert_file is None:
        argparser_.error('keyfile option requires certfile option')

    if opts.user is not None and opts.password is None:
        opts.password = _getpass.getpass('Enter password for %s: '
                                         % opts.user)

    if opts.user is not None or opts.password is not None:
        creds = (opts.user, opts.password)

    if opts.timeout is not None:
        if opts.timeout < 0 or opts.timeout > 300:
            argparser_.error('timeout option(%s) out of range' % opts.timeout)

    # if client cert and key provided, create dictionary for
    # wbem connection
    x509_dict = None
    if opts.cert_file is not None:
        x509_dict = {"cert_file": opts.cert_file}
        if opts.key_file is not None:
            x509_dict.update({'key_file': opts.key_file})

    conn = WBEMConnection(url, creds, default_namespace=opts.namespace,
                          no_verification=opts.no_verify_cert,
                          x509=x509_dict, ca_certs=opts.ca_certs,
                          timeout=opts.timeout)

    conn.debug = True

    return conn


class _WbemcliCustomFormatter(_SmartFormatter,
                              _argparse.RawDescriptionHelpFormatter):
    """
    Define a custom Formatter to allow formatting help and epilog.

    argparse formatter specifically allows multiple inheritance for the
    formatter customization and actually recommends this in a discussion
    in one of the issues:

        http://bugs.python.org/issue13023

    Also recommended in a StackOverflow discussion:

    http://stackoverflow.com/questions/18462610/argumentparser-epilog-and-description-formatting-in-conjunction-with-argumentdef
    """
    pass


def main(prog):
    usage = '%(prog)s [options] server'
    desc = """
Compile the test mof into a running WBEM Server defined by the command
inputs
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
        add_help=False, formatter_class=_WbemcliCustomFormatter)

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
        '-n', '--namespace', dest='namespace', metavar='namespace',
        default='root/cimv2',
        help='R|Default namespace in the WBEM server for operation\n'
             'requests when namespace option not supplied with\n'
             'operation request.\n'
             'Default: %(default)s')
    server_arggroup.add_argument(
        '-t', '--timeout', dest='timeout', metavar='timeout', type=int,
        default=None,
        help='R|Timeout of the completion of WBEM Server operation\n'
             'in seconds(integer between 0 and 300).\n'
             'Default: No timeout')

    security_arggroup = argparser.add_argument_group(
        'Connection security related options',
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
        help='Client will not verify certificate returned by the WBEM'
             ' server (see cacerts). This bypasses the client-side'
             ' verification of the server identity, but allows'
             ' encrypted communication with a server for which the'
             ' client does not have certificates.')
    security_arggroup.add_argument(
        '--cacerts', dest='ca_certs', metavar='cacerts',
        help='R|File or directory containing certificates that will be\n'
             'matched against a certificate received from the WBEM\n'
             'server. Set the --no-verify-cert option to bypass\n'
             'client verification of the WBEM server certificate.\n'
             'Default: Searches for matching certificates in the\n'
             'following system directories:\n' +
        ("\n".join("%s" % p for p in get_default_ca_cert_paths())))

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

    general_arggroup = argparser.add_argument_group(
        'General options')
    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Print more messages while processing')
    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    args = argparser.parse_args()

    if not args.server:
        argparser.error('No WBEM server specified')

    # Set up a client connection
    conn = _remote_connection(args.server, args, argparser)
    global SCRIPT_DIR
    SCRIPT_DIR = _os.path.dirname(__file__)

    try:
        conn.GetClass('PyWBEM_Person')
        print('Classes already exist in server. Terminating.')
        return
    except CIMError:
        pass

    mof_file = _os.path.join(SCRIPT_DIR, 'test.mof')

    compile_mof(conn, mof_file, args.namespace)

    test_compiled_mof(conn)


if __name__ == '__main__':
    main(_os.path.basename(_sys.argv[0]))
