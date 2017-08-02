#!/usr/bin/env python

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
    test wbemcli script.  This test generates a cmdline that calls
    wbemcli with a specific set of options and tests the returns.
    Because wbemcli always goes to interactive mode, the test call
    includes a wbemcli script that forces wbemcli to quit.

    It dynamically generates the set of tests from the TEST_MAP table.
"""

from __future__ import print_function, absolute_import
import os
import unittest
import re
from subprocess import Popen, PIPE
from collections import namedtuple
import six

# Output fragments to test against for each test defined
# Each item is a list of fragmants that are tested against the cmd execution
# result
HELP_OUTPUT = ['-n namespace, --namespace',
               '-t timeout, --timeout']
LOG_DEST_STDERR_OUTPUT = ['log=on',
                          'Connection: http://blah,',
                          ' no creds']
LOG_DEST_FILE_OUTPUT = ['log=on',
                        'Connection: http://blah,',
                        ' no creds']

TIMEOUT_OUTPUT = ['Connection: http://blah,',
                  ' no creds',
                  'timeout=10']

STATS_OUTPUT = ['Connection: http://blah,',
                ' no creds',
                'stats=on']
NAMESPACE_OUTPUT = ['log=off',
                    'Connection: http://blah,',
                    ' no creds',
                    'default-namespace=rex/fred']
LOG_STDERR_OUTPUT = ['pywbem.ops-Connection:']

DEF_NAMESPACE_OUTPUT = ['default-namespace=root/cimv2']


# pylint: disable=invalid-name
tst_def = namedtuple('tst_def', ['test_name',
                                 'cmd',
                                 'expected_stdout',
                                 'expected_exitcode',
                                 'expected_stderr'])

# Each test in the following list is a namedtuple containing test definition.
TESTS_MAP = [  # pylint: disable=invalid-name
    tst_def('help', '--help', HELP_OUTPUT, 0, None),
    tst_def('namespace', '-n rex/fred', NAMESPACE_OUTPUT, 0, None),
    tst_def('timeout', '-t 10', TIMEOUT_OUTPUT, 0, None),
    tst_def('log_dest_file1', '-l ops=file', LOG_DEST_FILE_OUTPUT, 0, None),
    tst_def('log_dest_file1a', '-l ops=file:min', LOG_DEST_FILE_OUTPUT, 0,
            None),
    tst_def('log_dest_file1b', '-l ops=file:min:debug', LOG_DEST_FILE_OUTPUT, 0,
            None),
    tst_def('log_dest_file2', '-l http=file', LOG_DEST_FILE_OUTPUT, 0, None),
    tst_def('log_dest_file3', '-l all=file', LOG_DEST_FILE_OUTPUT, 0, None),
    tst_def('log_dest_file4', '-l ops=stderr:all:debug', LOG_DEST_FILE_OUTPUT,
            0, LOG_STDERR_OUTPUT),
    tst_def('log_dest_file5', '-l all=stderr:all:debug', LOG_DEST_FILE_OUTPUT,
            0, LOG_STDERR_OUTPUT),
    tst_def('def_namespace', '', DEF_NAMESPACE_OUTPUT, 0, None),
    tst_def('error_param', '--log', None, 2,
            ['argument -l/--log: expected one argument']), ]


def create_abs_path(filename):
    """
    create an absolute path name for filename in the same directory as this
    python code.  Also, replace any backslashes with forward slashes to
    account for executing this in windows.
    """
    script_dir = os.path.dirname(__file__)
    script_file = os.path.join(script_dir, filename)
    return script_file.replace('\\', '/')


class ContainerMeta(type):
    """Metaclass to define the function to generate unittest methods."""

    def __new__(mcs, name, bases, dict):  # pylint: disable=redefined-builtin
        def generate_test(test_name, test_params):
            """
            Defines the test method (test_<name>) that we generate for each test
            and returns the method.

            The cmd_str defines ONLY the arguments and options part of the
            command.  This function prepends wbemcli to the cmd_str.

            Since wbemcli is interactive, it also includes a quit script

            Each test builds the pywbemcli command executes it and tests the
            results
            """

            def test(self):  # pylint: disable=missing-docstring
                """ The test method that is generated."""
                # create the path for the quit script
                quit_script_file = create_abs_path('wbemcli_quit_script.py')

                script_name = 'wbemcli.bat' if os.name == 'nt' else 'wbemcli'

                cmd = ('%s http://blah %s -s %s' % (script_name,
                                                    test_params.cmd,
                                                    quit_script_file))
                # Disable python warnings for wbemcli call
                # because some imports generate deprecated warnings
                # that appear in std_err when nothing expected

                bash_cmd = 'bash -c "set -o pipefail;  PYTHONPATH=. ' \
                           'PYTHONWARNINGS= %s"' % cmd

                proc = Popen(bash_cmd, shell=True, stdout=PIPE, stderr=PIPE)
                std_out, std_err = proc.communicate()
                exitcode = proc.returncode
                # print('bash_cmd: %s\nexitcode: %s std_out:\n%s\nstd_err:'
                #      '\n%s' % (bash_cmd, exitcode, std_out, std_err))

                if six.PY3:
                    std_out = std_out.decode()
                    std_err = std_err.decode()

                if test_params.expected_exitcode is not None:
                    self.assertEqual(exitcode, test_params.expected_exitcode,
                                     ('Test %s: Unexpected ExitCode Err. '
                                      'Expected %s: cmd="%s": '
                                      'exitcode %s: stderr=%s' %
                                      (test_name, test_params.expected_exitcode,
                                       cmd,
                                       exitcode, std_err)))

                if test_params.expected_stderr is None:
                    if re.search('ImportWarning', std_err) is None:
                        self.assertEqual(std_err, "",
                                         'Test %s stderr not empty as '
                                         'expected. Returned %s'
                                         % (test_name, std_err))
                    else:
                        print('Ignored junk in stderr %s' % std_err)
                    self.assertEqual(std_err, "",
                                     'Test %s stderr not empty as expected. '
                                     'Returned %s'
                                     % (test_name, std_err))
                else:
                    for item in test_params.expected_stderr:
                        match_result = re.search(item, std_err)
                        self.assertNotEqual(match_result, None, 'Test %s, '
                                            'stderr did not match test '
                                            'definition. Expected %s in %s' %
                                            (test_name, item, std_err))
                if test_params.expected_stdout is not None:
                    for item in test_params.expected_stdout:
                        match_result = re.search(item, std_out)
                        self.assertNotEqual(match_result, None,
                                            'Test=%s, stdout did not match '
                                            'test definition. Expected %s in %s'
                                            % (test_name, item, std_out))
                else:
                    self.assertEqual(std_out, "",
                                     'Test %s stdout not empty as expected. '
                                     'Returned %s'
                                     % (test_name, std_out))
            return test

        # generate the individual from TESTS_MAP list
        for test_params in TESTS_MAP:
            test_name = "test_%s" % test_params.test_name
            dict[test_name] = generate_test(test_name, test_params)
        return type.__new__(mcs, name, bases, dict)


@six.add_metaclass(ContainerMeta)
class TestsContainer(unittest.TestCase):
    """Container class for all tests created from ContainerMeta"""
    __metaclass__ = ContainerMeta


if __name__ == '__main__':
    unittest.main()
