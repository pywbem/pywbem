#!/usr/bin/env python

"""
    Example of using Iterator Operations to retrieve instances from a
    WBEM Server. This example executes the IterEnumerateInstances and the
    corresponding IterEnumeratePaths operations.

    It:
        Creates a connection
        Opens an enumeration session with OpenEnumerateInstances
        Executes a pull loop until the result.eos =True
        Displays overall statistics on the returns
    It also displays the results of the open and each pull in detail
"""


import sys
import argparse as _argparse
from pywbem import WBEMConnection, CIMError, Error

def _str_to_bool(str_):
    """Convert string to bool (in argparse context)."""
    if str_.lower() not in ['true', 'false', 'none']:
        raise ValueError(f'Need bool; got {str_!r}')
    return {'true': True, 'false': False, 'none': None}[str_.lower()]

def add_nullable_boolean_argument(parser, name, default=None, help_=None):
    """Add a boolean argument to an ArgumentParser instance."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--' + name, nargs='?', default=default, const=True, type=_str_to_bool,
        help=help_)
    group.add_argument('--no' + name, dest=name, action='store_false',
                       help=help_)

def create_parser(prog):
    """
    Parse command line arguments, connect to the WBEM server and open the
    interactive shell.
    """

    usage = '%(prog)s [options] server'
    desc = 'Provide an interactive shell for issuing operations against' \
           ' a WBEM server.'
    epilog = f"""
Examples:
  {prog} https://localhost:15345 -n vendor -u sheldon -p penny
          - (https localhost, port=15345, namespace=vendor user=sheldon
         password=penny)

  {prog} http://[2001:db8::1234-eth0] -(http port 5988 ipv6, zone id eth0)
"""

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')
    pos_arggroup.add_argument(
        'server', metavar='server', nargs='?',
        help='Host name or URL of the WBEM server in format: '
             '"[{scheme}://]{host}[:{port}]", where '
             'scheme can be "https" (default) or "http", and '
             'port defaults to 5988 for http and 5989 for https.')

    server_arggroup = argparser.add_argument_group(
        'Server related options',
        'Specify the WBEM server namespace and timeout')
    server_arggroup.add_argument(
        '-n', '--namespace', dest='namespace', metavar='namespace',
        default='root/cimv2',
        help='Default namespace in the WBEM server for operation '
             'requests when namespace option not supplied with '
             'operation request. '
             'Default: %(default)s')
    server_arggroup.add_argument(
        '-t', '--timeout', dest='timeout', metavar='timeout', type=int,
        default=None,
        help='Timeout of the completion of WBEM Server operation '
             'in seconds (integer between 0 and 300). '
             'Default: No timeout')

    server_arggroup.add_argument(
        '-c', '--classname', dest='classname', metavar='classname',
        default='CIM_ManagedElement',
        help='Classname in the WBEM server for operation request. '
             'Default: %(default)s')

    security_arggroup = argparser.add_argument_group(
        'Connection security related options',
        'Specify user name and password or certificates and keys')
    security_arggroup.add_argument(
        '-u', '--user', dest='user', metavar='user',
        help='User name for authenticating with the WBEM server. '
             'Default: No user name.')
    security_arggroup.add_argument(
        '-p', '--password', dest='password', metavar='password',
        help='Password for authenticating with the WBEM server. '
             'Default: Will be prompted for, if user name specified.')
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
        help='File or directory containing certificates that will be '
             'matched against a certificate received from the WBEM '
             'server. Set the --no-verify-cert option to bypass '
             'client verification of the WBEM server certificate. ')

    security_arggroup.add_argument(
        '--certfile', dest='cert_file', metavar='certfile',
        help='Client certificate file for authenticating with the '
             'WBEM server. If option specified the client attempts '
             'to execute mutual authentication. '
             'Default: Simple authentication.')
    security_arggroup.add_argument(
        '--keyfile', dest='key_file', metavar='keyfile',
        help='Client private key file for authenticating with the '
             'WBEM server. Not required if private key is part of the '
             'certfile option. Not allowed if no certfile option. '
             'Default: No client key file. Client private key should '
             'then be part  of the certfile')

    general_arggroup = argparser.add_argument_group(
        'General options')
    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Print more messages while processing')

    general_arggroup.add_argument(
        '-m', '--MaxObjectCount', dest='max_object_count',
        metavar='MaxObjectCount', default=100,
        help='Maximum object count in pull responses. '
             'Default: 100.')

    add_nullable_boolean_argument(
        general_arggroup, 'usepull',
        help_='Use Pull Operations.  If --usepull, pull will be used. If'
              ' --nousepull will execute Enumerate operation. Default is'
              ' `None` where the system decides.')
    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    return argparser

def parse_cmdline(argparser_):
    """ Parse the command line.  This tests for any required args"""

    opts = argparser_.parse_args()

    if not opts.server:
        argparser_.error('No WBEM server specified')
        return None
    return opts

def main():
    """
        Get arguments and call the execution function
    """
    prog = sys.argv[0]

    arg_parser = create_parser(prog)

    opts = parse_cmdline(arg_parser)

    print(f'Parameters: server={opts.server}\n username={opts.user}\n '
          f'namespace={opts.namespace}\n classname={opts.classname}\n '
          f'max_pull_size={opts.max_object_count}\n use_pull={opts.usepull}')

    # call method to connect to the server
    conn = WBEMConnection(opts.server, (opts.user, opts.password),
                          default_namespace=opts.namespace,
                          no_verification=True,
                          use_pull_operations=opts.usepull)

    #Call method to create iterator
    instances = []
    try:
        iter_instances = conn.IterEnumerateInstances(
            opts.classname,
            MaxObjectCount=opts.max_object_count)

        # generate instances with
        for instance in iter_instances:
            print(f' {type(instances)} {type(instance)}')
            instances.append(instance)
            print(f'\npath={instance.path}\n{instance.tomof()}')

    # handle exceptions
    except CIMError as ce:
        print(f'Operation Failed: CIMError: code={ce.status_code_name}, '
              f'Description={ce.status_description}')
        sys.exit(1)
    except Error as err:
        print(f"Operation failed: {err}")
        sys.exit(1)

    inst_paths = [inst.path for inst in instances]

    paths = []
    try:
        iter_paths = conn.IterEnumerateInstancePaths(
            opts.classname,
            MaxObjectCount=opts.max_object_count)

        # generate instances with
        for path in iter_paths:
            print(f'path={path}')
            paths.append(path)

        if len(paths) != len(paths):
            print('Error path and enum response sizes different '
                  f'enum={len(paths)} path={len(paths)}')
        for path in paths:
            found = False
            for inst_path in inst_paths:
                if path == inst_path:
                    found = True
                    break
                else:
                    print(f'No match \n{path}\n{inst_path}')
            if not found:
                print(f'Path {path} not found in insts')
    # handle exceptions
    except CIMError as ce:
        print(f'Operation Failed: CIMError: code={ce.status_code_name}, '
              f'Description={ce.status_description}')
        sys.exit(1)
    except Error as err:
        print (f"Operation failed: {err}")
        sys.exit(1)

    return 0

if __name__ == '__main__':
    sys.exit(main())
