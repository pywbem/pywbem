#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""
    Test wbemcli script.  This test generates a cmdline that calls
    wbemcli with a specific set of options and tests the returns.
    Because wbemcli always goes to interactive mode, the test call
    includes a wbemcli script that forces wbemcli to quit.

    It dynamically generates the set of tests from the TEST_MAP table
    where each test is a call to execute wbemcli with a particular set of
    arguments and options. It then tests the stdout, stderr, and exitcode
    against the TEST_MAP.

    This test does not test the individual operations that can be executed,
    just the initialization components for wbemcli
"""

from __future__ import print_function, absolute_import
import os
import pytest

from .utils.cmd_line_test_utils import wbemcli_test

TEST_DIR = os.path.dirname(__file__)
TEST_MOCK_MOF = os.path.join(TEST_DIR, 'simple_mock_model.mof')

VERBOSE = False  # Verbose mode for the testcases


def create_abs_path(filename):
    """
    Create an absolute path name for filename in the same directory as this
    python code.
    """
    script_dir = os.path.dirname(__file__)
    return os.path.join(script_dir, filename)


WBEMCLI_HELP = """usage: wbemcli [options] server

Provide an interactive shell for issuing operations against a WBEM server.

wbemcli executes the WBEMConnection as part of initialization so the user can
input requests as soon as the interactive shell is started.

Use h() in thenteractive shell for help for wbemcli methods and variables.

Positional arguments:
  server                Host name or url of the WBEM server in this format:
                            [{scheme}://]{host}[:{port}]
                        - scheme: Defines the protocol to use;
                            - "https" for HTTPs protocol
                            - "http" for HTTP protocol.
                          Default: "https".
                        - host: Defines host name as follows:
                             - short or fully qualified DNS hostname,
                             - literal IPV4 address(dotted)
                             - literal IPV6 address (RFC 3986) with zone
                               identifier extensions(RFC 6874)
                               supporting "-" or %25 for the delimiter.
                        - port: Defines the WBEM server port to be used
                          Defaults:
                             - HTTP  - 5988
                             - HTTPS - 5989

Server related options:
  Specify the WBEM server namespace and timeout

  -n namespace, --namespace namespace
                        Default namespace in the WBEM server for operation
                        requests when namespace option not supplied with
                        operation request.
                        Default: root/cimv2
  -t timeout, --timeout timeout
                        Timeout of the completion of WBEM Server operation
                        in seconds(integer between 0 and 300).
                        Default: No timeout

Connection security related options:
  Specify user name and password or certificates and keys

  -u user, --user user  User name for authenticating with the WBEM server.
                        Default: No user name.
  -p password, --password password
                        Password for authenticating with the WBEM server.
                        Default: Will be prompted for, if user name
                        specified.
  -nvc, --no-verify-cert
                        Client will not verify certificate returned by the
                        WBEM server (see cacerts). This bypasses the client-
                        side verification of the server identity, but allows
                        encrypted communication with a server for which the
                        client does not have certificates.
  --cacerts cacerts     File or directory containing certificates that will be
                        matched against a certificate received from the WBEM
                        server. Set the --no-verify-cert option to bypass
                        client verification of the WBEM server certificate.
                        Default: Searches for matching certificates in the
                        following system directories:
                        /etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt
                        /etc/ssl/certs
                        /etc/ssl/certificates
  --certfile certfile   Client certificate file for authenticating with the
                        WBEM server. If option specified the client attempts
                        to execute mutual authentication.
                        Default: Simple authentication.
  --keyfile keyfile     Client private key file for authenticating with the
                        WBEM server. Not required if private key is part of the
                        certfile option. Not allowed if no certfile option.
                        Default: No client key file. Client private key should
                        then be part  of the certfile

General options:
  -s [scripts [scripts ...]], --scripts [scripts [scripts ...]]
                        Execute the python code defined by the script before the
                        user gets control. This argument may be repeated to load
                        multiple scripts or multiple scripts may be listed for a
                        single use of the option. Scripts are executed after the
                        WBEMConnection call
  -v, --verbose         Print more messages while processing
  -V, --version         Display pywbem version and exit.
  --statistics          Enable gathering of statistics on operations.
  --mock-server [file name [file name ...]]
                        Activate pywbem_mock in place of a live WBEMConnection and
                        compile/build the files defined (".mof" suffix or "py" suffix.
                        MOF files are compiled and python files are executed assuming
                        that they include mock_pywbem methods that add objects to the
                        repository.
  -l log_spec[,logspec], --log log_spec[,logspec]
                        Log_spec defines characteristics of the various named
                        loggers. It is the form:
                         COMP=[DEST[:DETAIL]] where:
                           COMP:   Logger component name:[api|http|all].
                                   (Default=all)
                           DEST:   Destination for component:[file|stderr].
                                   (Default=file)
                           DETAIL: Detail Level to log: [all|paths|summary] or
                                   an integer that defines the maximum length of
                                   of each log record.
                                   (Default=all)
  -h, --help            Show this help message and exit

Examples:
  wbemcli https://localhost:15345 -n vendor -u sheldon -p penny
          - (https localhost, port=15345, namespace=vendor user=sheldon
         password=penny)

  wbemcli http://[2001:db8::1234-eth0] -(http port 5988 ipv6, zone id eth0)
"""  # noqa=E501

# pylint: disable=line-too-long


TEST_SCRIPT = """
#
#  This script tests a number of the WBEM operation methods as defined
#  for wbemcli. It executes the commands and then asserts for the expected
#  results.  This script tests the enumerate and get for class, instance, and
#  qualifier operations.
#
from wbemcli import CONN, gc, ecn, ei, iei, oei, piwp, ein, ieip, oeip, pip, \
    a, iai, oai, an, iaip, oaip, iri, ori, rn, irip, orip, ec, gq, eq

print('CONN %s' % CONN)

qual_decls = eq()
# print('QUALIFIER_DECLARATIONS %s' % qual_decls)
assert 'Association' in [qd.name for qd in qual_decls]

qualifier = gq('Association')
# print('QUALIFIER %s' % qualifier)
assert qualifier.name == 'Association'

class_names = ecn()
# print('CLASSNAMES %s' % class_names)
assert class_names == ['CIM_Foo']

clns = ecn(di=True)
assert all(x in clns for x in ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2',
                               'CIM_Foo_sub_sub'])
inames = ein('CIM_Foo')
assert len(inames) == 3
assert 'root/cimv2:CIM_Foo.InstanceID="CIM_Foo1"' in [str(n) for n in inames]

# Test get instance for each instance name in inst_nmes
for name in inames:
    inst = gi(name)
    inst_mof = inst.tomof()
    assert inst_mof.startswith('instance of CIM_Foo {')
    print(inst.tomof())
    assert inst.path in inames

quit()
# end of script

"""


# Script that contains a syntax error
TEST_SCRIPT_ERR = 'printx("TEST"); quit()'


QUIT_SCRIPT = """
import sys
# The following is required because wbemcli executes the scripts before
# generating the infomation about connections.  This allows that info to
# be tested as part of stdout return.
from wbemcli import _get_connection_info
print(_get_connection_info())

sys.stdout.flush()
sys.stderr.flush()
quit()

"""

OK = True  # mark tests OK when they execute correctly
RUN = True  # Mark OK = False and current test case being created RUN
FAIL = False  # Any test currently FAILING or not tested yet


TEST_CASES = [
    # desc - String describing the test
    # args - List of arguments. Each argument must be separate member of list
    # exp_response - Dictionary defining expected response. The keywords are:
    #    stdout - Expected response in stdout
    #    stderr - Expected response in stderr
    #    rc - Expected return code. If entry does not exist, 0 is expected
    #    test - Specific test on response.  The allowed tests are defined in
    # mock - Files to be included as attributes of the --mock_server option
    # script - Text for script to be executed by wbemcli with --scripts option
    # condition - Expected test condition

    #
    #   --help
    #
    ['Verify wbemcli help',
     '--help',
     {'stdout': WBEMCLI_HELP,
      'test': 'lines'},
     None, None, OK],

    ['Verify output for log on api=file',
     ['http://blah', '-l', 'api=file'],
     {'stdout': ['log=on', 'Connection: http://blah', ' no creds',
                 'default-namespace=root/cimv2'],
      'test': 'in'},
     None, None, OK],

    ['Verify output for timeout on',
     ['http://blah', '-t', '10'],
     {'stdout': ['timeout=10', 'Connection: http://blah', ' no creds'],
      'test': 'in'},
     None, None, OK],

    ['Verify log definition api=file, connection message',
     ['http://blah', '-l', 'api=file'],
     {'stdout': ['log=on', 'Connection: http://blah', ' no creds'],
      'test': 'in'},
     None, None, OK],

    ['Verify output for log http=file, connection message',
     ['http://blah', '-l', 'http=file'],
     {'stdout': ['log=on', 'Connection: http://blah', ' no creds'],
      'test': 'in'},
     None, None, OK],

    ['Verify output for log all=file, connection message',
     ['http://blah', '-l', 'all=file'],
     {'stdout': ['log=on', 'Connection: http://blah', ' no creds'],
      'test': 'in'},
     None, None, OK],

    ['Verify output for log api=stderr, connection message',
     ['http://blah', '-l', 'api=stderr'],
     {'stdout': ['log=on', 'Connection: http://blah', ' no creds'],
      'test': 'in'},
     None, None, OK],

    ['Validate default default_namespace',
     ['http://localhost'],
     {'stdout': ['Connection: http://localhost', ' no creds',
                 'default-namespace=root/cimv2'],
      'test': 'in'},
     None, None, OK],

    ['Validate user set  default_namespace',
     ['http://localhost', '-n', 'root/blah'],
     {'stdout': ['Connection: http://localhost', ' no creds',
                 'default-namespace=root/blah'],
      'test': 'in'},
     None, None, OK],

    ['Validate load mock mof file',
     [],
     {'stdout': ['Connection: http://FakedUrl', ' no creds',
                 'default-namespace=root/cimv2'],
      'test': 'in'},
     TEST_MOCK_MOF, None, OK],

    ['Validate script load and run. Tests for various operations are in script',
     [],
     {'stdout': ['instance of CIM_Foo', 'InstanceID = "CIM_Foo1";'],
      'test': 'in'},
     TEST_MOCK_MOF, TEST_SCRIPT, OK],

    # TODO: Extend the above to include createinstance
    # TODO: Add invokemethod test. This requires using another mock file
    # TODO: Extend the above to include a mock for associations and refs.
    #       The mock defs for these operations will be in a separate script.
    # TODO: Extend the tests to cover more of the command options (ex.
    #       propertylists, etc.)
    # TODO: We cannot create a test for invalid script because the code
    #       creates the script from a python string in the test definition.
    #       Should find a way to confirm that an invalid file gens error

    #
    #   Test that errors are correctly handled.
    #

    ['Validate invalid url fails',
     ['httpx://localhost'],
     {'stderr': ['error: Invalid scheme on server argument. '
                 'Use "http" or "https"'],
      'rc': 2,
      'test': 'v'},
     None, None, OK],

    ['Validate load invalid mock file fails.',
     ['httpx://localhost', '--mock-server', 'blah.mof'],
     {'stderr': ['error: Build Repository failed: File name blah.mof'],
      'rc': 2,
      'test': 'in'},
     None, None, OK],

    ['Verify invalid timeout param',
     ['http://blah', '-t', 'blah'],
     {'stderr': ["error: argument -t/--timeout: invalid int value: 'blah'"],
      'rc': 2,
      'test': 'in'},
     None, None, OK],

    ['Validate invalid script fails',
     [],
     {'stderr': ["NameError: name 'printx' is not defined"],
      'rc': 1,
      'test': 'in'},
     TEST_MOCK_MOF, TEST_SCRIPT_ERR, OK],
]


@pytest.mark.parametrize(
    "desc, args, exp_response, mock, script, condition",
    TEST_CASES)
def test_command(desc, args, exp_response, mock, script, condition):
    """
    Standard test for pywbemcli commands using pytest
    """
    if not condition:
        pytest.skip("Condition for test case %s not met" % desc)

    script_file_name = create_abs_path("wbemclitestscript.py")

    if script:
        with open(script_file_name, "w") as text_file:
            text_file.write(script)
        args.append("--script")
        args.append(script_file_name)
    else:
        # If not help command, do quit() script to terminate wbemcli
        if not any(s in args for s in ['-h', '--help']):
            with open(script_file_name, "w") as text_file:
                text_file.write(QUIT_SCRIPT)
            args.append("--script")
            args.append(script_file_name)

    try:
        wbemcli_test(desc, args, exp_response, mock, condition, verbose=VERBOSE)

    finally:
        if os.path.isfile(script_file_name):
            os.remove(script_file_name)
