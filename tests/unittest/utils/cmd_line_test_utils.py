# Copyright 2017 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utilities to test wbemcli as a separate executable.  These tools are
based on pytest.  They provide the cmd line execution function(wbemcli_test)
and a function to test wbemcli with input parameter options and use both
mock-server and scripts to execute code in wbemcli.

All tests complete because if there is no script it is not a request for the
help response, a script that exists wbemcli is created and passed to wbemcli.
Without this, wbemcli would drop into the interactive loop after starting.
"""

from __future__ import absolute_import, print_function

import os
import re
from subprocess import Popen, PIPE
import pytest
import six

TEST_DIR = os.path.dirname(__file__)


def wbemcli_test(desc, args, exp_response, mock_file, condition, verbose=False):
    # pylint: disable=line-too-long
    """
    Test method to execute a test on wbemcli by calling the executable wbemcli
    with arguments defined by args. This can execute wbemcli either with a mock
    environment by using the mock_file variable or without mock if the
    mock_file parameter is None. It also allows adding scripts to the command
    so that wbemcli can be commanded to execute some functionality. The method
    tests the results of the execution of wbemcli using the exp_response
    parameter.

    Parameters:
      desc (:term:`string`):
        Description of the test

      args (:class:`py:list` of :term:`string` or :term:`string`):
        The set of arguments to append after the command name

      exp_response (:class:`py:dict`)

        Keyword arguments for expected response.

        Includes the following possible keys:

          'stdout' or 'stderr' - Defines which return is expected (the
          expected response). The value is a string or iterable defining
          the data expected in the response. The data definition in
          this dictionary entry must be compatible with the definition
          of expected data for the test selected.
          Only one of these keys may exist.

          'test' - If it exists defines the test used to compare the
          returned data with the expected returned data defined as the
          value of 'stdout'/'stderr'.

          The tests defined are:

            'startswith' - Expected Response must be a single string
            The returned text defined starts with the defined string

            'lines' -  Expected response may be either a list of strings or
            single string

            Compares for exact match between the expected response and the
            returned data line by line. The number of lines and the data
            in each line must match.  If the expected response is a single
            string is is split into lines separated at each new line
            before the match

            'patterns' - Expected response must be same as lines test
            except that each line in the expected response is treated as
            a regex expression and a regex match is executed for each line.

            'regex' - Expected response is a single string or list of
            strings. Each string is considered a regex expression. Compared
            each string in expected response against the returned data using
            match.

            'in' - Expected response is string or list of strings.
            This tests executes compare each string in expected response
            against the complete actual response to determine if each entry
            in expected response is in the response data.

          'rc' expected exit_code from pywbemcli.  If None, code 0
          is expected.

      mock_file (:term:`string` or list of :term:`string` or None):
        If this is a string, this test will be executed using the
        --mock-server pywbemcl option with this file as the name of the
        objects to be compiled. This should be just a file name and
        this method assumes the file is in the directory where the
        module of this function is located.

        If it is a list, each string in the list will be added to the
        attributes of the --mock-server option

        If None, test is executed without the --mock-server input parameter
        and defines an artificial server name  Used to test subcommands
        and options that do not communicate with a server.  It is faster
        than installing the mock repository

      condition (None or False):
        If False, the test is skipped
    """  # noqa: E501
    # pylint: enable=line-too-long

    if not condition:
        pytest.skip("Condition for test case %s not met" % desc)

    elif isinstance(args, six.string_types):
        args = args.split(" ")
    elif not isinstance(args, (list, tuple)):
        assert 'Invalid args input to test %r . Allowed types are dict, ' \
               'string, list, tuple.' % args

    cmd_line = []

    if mock_file:
        if isinstance(mock_file, six.string_types):
            mock_file = [mock_file]
        for mf in mock_file:
            cmd_line.extend(['--mock-server',
                             os.path.join(TEST_DIR, mf)])

    if args:
        cmd_line.extend(args)

    if 'stdout' in exp_response and 'stderr' in exp_response:
        assert False, 'Both stdout and stderr not allowed'

    rc, stdout, stderr = execute_wbemcli(cmd_line, verbose=verbose)

    exp_rc = exp_response['rc'] if 'rc' in exp_response else 0
    assert_rc(exp_rc, rc, stdout, stderr)

    test_value = None
    component = None
    if 'stdout' in exp_response:
        test_value = exp_response['stdout']
        rtn_value = stdout
        component = 'stdout'
    elif 'stderr' in exp_response:
        test_value = exp_response['stderr']
        rtn_value = stderr
        component = 'stderr'
    else:
        assert False, 'Expected "stdout" or "stderr" key. One of these ' \
                      'keys required in exp_response.'
    if test_value:
        if 'test' in exp_response:
            test = exp_response['test']
            # test that rtn_value starts with test_value
            if test == 'startswith':
                assert isinstance(test_value, six.string_types)
                assert rtn_value.startswith(test_value), \
                    "{0}\n{1}={2!r}".format(desc, component, rtn_value)
            # test that lines match between test_value and rtn_value
            # base on regex match
            elif test == 'patterns':
                if isinstance(test_value, six.string_types):
                    test_value = test_value.splitlines()
                assert isinstance(test_value, (list, tuple))
                assert_patterns(test_value, rtn_value.splitlines(),
                                "{0}\n{1}={2}".format(desc, component,
                                                      rtn_value))
            # test that each line in the test value matches the
            # corresponding line in the rtn_value exactly
            elif test == 'lines':
                if isinstance(test_value, six.string_types):
                    test_value = test_value.splitlines()
                if isinstance(test_value, (list, tuple)):
                    assert_lines(test_value, rtn_value.splitlines(),
                                 "{0}\n{1}={2}".format(desc, component,
                                                       rtn_value))
                else:
                    assert(isinstance(test_value, six.string_types))
                    assert_lines(test_value.splitlines(),
                                 rtn_value.splitlines(),
                                 "{0}\n{1}={2}".format(desc, component,
                                                       rtn_value))
            # test with a regex search that all values in list exist in
            # the return
            elif test == 'regex':
                if isinstance(test_value, (tuple, list)):
                    rtn_value = rtn_value.join("\n")
                elif isinstance(test_value, six.string_types):
                    rtn_value = [rtn_value]
                else:
                    assert False, "regex expected response must be string" \
                                  "or list of strings. %s found" % \
                                  type(rtn_value)

                for regex in test_value:
                    assert isinstance(regex, six.string_types)
                    match_result = re.search(regex, rtn_value)
                    assert not match_result, \
                        "DESC:{0}\nEXP:{1}\nRTN:{2}".format(desc, re, rtn_value)
            elif test == 'in':
                if isinstance(test_value, six.string_types):
                    test_value = [test_value]
                for test_str in test_value:
                    assert test_str in rtn_value, \
                        "DESC:{0}\nEXP:{1}\nRTN:{2}".format(desc, test_str,
                                                            rtn_value)
            else:
                assert 'Test %s is invalid. Skipped' % test


def execute_wbemcli(args, verbose=False):
    """
    Invoke the 'wbemcli' command as a child process.

    This requires that the 'wbemcli' command is installed in the current
    Python environment.

    Parameters:

      args (iterable of :term:`string`): Command line arguments, without the
        command name.
        Each single argument must be its own item in the iterable; combining
        the arguments into a string does not work.
        The arguments may be binary strings encoded in UTF-8, or unicode
        strings.

    Returns:

      tuple(rc, stdout, stderr): Output of the command, where:

        * rc(int): Exit code of the command.
        * stdout(:term:`unicode string`): Standard output of the command,
          as a unicode string with newlines represented as '\\n'.
          An empty string, if there was no data.
        * stderr(:term:`unicode string`): Standard error of the command,
          as a unicode string with newlines represented as '\\n'.
          An empty string, if there was no data.
    """

    cli_cmd = u'wbemcli.bat' if os.name == 'nt' else u'wbemcli'

    assert isinstance(args, (list, tuple))
    cmd_args = [cli_cmd]
    for arg in args:
        if not isinstance(arg, six.text_type):
            arg = arg.decode('utf-8')
        cmd_args.append(arg)
    cmd_args = u' '.join(cmd_args)

    if verbose:
        print('Calling with shell: %r' % cmd_args)

    # Using universal_newlines=True reduces EOLs to
    # '\n' despite what other packages might add on.
    proc = Popen(cmd_args, shell=True, stdout=PIPE, stderr=PIPE,
                 universal_newlines=True)
    stdout_str, stderr_str = proc.communicate()
    rc = proc.returncode

    if isinstance(stdout_str, six.binary_type):
        stdout_str = stdout_str.decode('utf-8')
    if isinstance(stderr_str, six.binary_type):
        stderr_str = stderr_str.decode('utf-8')

    return rc, stdout_str, stderr_str


def assert_rc(exp_rc, rc, stdout, stderr):
    """
    Assert that the specified return code is as expected.

    The actual return code is compared with the expected return code,
    and if they don't match, stdout and stderr are displayed as a means
    to help debugging the issue.

    Parameters:

      exp_rc (int): expected return code.

      rc (int): actual return code.

      stdout (string): stdout of the command, for debugging purposes.

      stderr (string): stderr of the command, for debugging purposes.
    """

    assert exp_rc == rc, \
        "Unexpected exit code (expected {0}, got {1})\n" \
        "  stdout:\n" \
        "{2}\n\n" \
        "  stderr:\n" \
        "{3}". \
        format(exp_rc, rc, stdout, stderr)


def assert_patterns(exp_patterns, act_lines, meaning):
    """
    Assert that the specified lines match the specified patterns.

    The patterns are matched against the complete line from begin to end,
    even if no begin and end markers are specified in the patterns.

    Parameters:

      exp_patterns (iterable of string): regexp patterns defining the expected
        value for each line.

      act_lines (iterable of string): the lines to be matched.

      meaning (string): A short descriptive text that identifies the meaning
        of the lines that are matched, e.g. 'stderr'.
    """
    assert len(act_lines) == len(exp_patterns), \
        "Unexpected number of lines in test desc: {0}:\n" \
        "Expected line cnt={1}:\n" \
        "{2}\n\n" \
        "Actual line cnt={3}:\n" \
        "{4}\n". \
        format(meaning, len(act_lines), '\n'.join(act_lines),
               len(exp_patterns), '\n'.join(exp_patterns))

    for i, act_line in enumerate(act_lines):
        exp_line = exp_patterns[i]
        # if not exp_line.endswith('$'):
        #    exp_line += '$'
        assert re.match(exp_line, act_line), \
            "Unexpected line {0} in test desc:{1}:\n" \
            "Expected line vs. actual line:\n" \
            "------------\n" \
            "{2}\n" \
            "------------\n" \
            "{3}\n" \
            "------------\n". \
            format(i, meaning, exp_line, act_line)


def assert_lines(exp_lines, act_lines, meaning):
    """
    Assert that the specified lines match exactly the lines specified in
    exp_lines. This does not require that the pattern lines escape any
    special characters, etc.

    The exp_lines are matched against the complete line from begin to end. The
    test stops at the first difference

    Parameters:

      exp_lines (iterable of string): the expected string for each line.

      act_lines (iterable of string): the lines to be matched.

      meaning (string): A short descriptive text that identifies the meaning
        of the lines that are matched, e.g. 'stderr'.
    """
    assert len(act_lines) == len(exp_lines), \
        "Unexpected number of lines in {0}:\n" \
        "Expected lines cnt={1}:\n" \
        "{2}\n" \
        "Actual lines cnt={3}:\n" \
        "{4}\n". \
        format(meaning, len(exp_lines), '\n'.join(exp_lines),
               len(act_lines), '\n'.join(act_lines))

    for i, act_line in enumerate(act_lines):
        exp_line = exp_lines[i]
        assert exp_line == act_line, \
            "Unexpected line {0} in {1}:\n" \
            "  expected line vs. actual line:\n" \
            "------------\n" \
            "{2}\n" \
            "{3}\n" \
            "------------\n". \
            format(i, meaning, exp_line, act_line)
