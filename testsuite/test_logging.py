#!/usr/bin/env python

# Copyright 2017 InovaDevelopment Inc.
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
"""
Unit test logging functionality in _logging.py

"""

from __future__ import absolute_import, print_function

import os

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import unittest
from testfixtures import LogCapture, log_capture

from pywbem import PywbemLoggers, LOG_OPS_CALLS_NAME
from pywbem._logging import get_logger

VERBOSE = False

# Location of any test scripts for testing wbemcli.py
SCRIPT_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_logging.log'
TEST_OUTPUT_LOG = '%s/%s' % (SCRIPT_DIR, LOG_FILE_NAME)


class BaseLoggingTests(unittest.TestCase):
    """Base class for logging unit tests"""

    def setUp(self):
        # reset the PywbemLoggers store for the next test.  This forces
        # the dictionary back to empty. Since this is a class variable
        # we clear it at the class level.
        PywbemLoggers.loggers = {}

    def tearDown(self):
        LogCapture.uninstall_all()
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class TestLogParse(BaseLoggingTests):
    """
    Test parse_log_specs
    """
    def parser_test(self, param, expected_result):
        """ Common test for successful parsing"""
        # pylint: disable=protected-access
        result = PywbemLoggers._parse_log_specs(param)
        self.assertEqual(result, expected_result)

    def test_comp_only(self):
        """Test all string"""
        param = 'all'
        self.parser_test(param, {'all': (None, None)})

    def test_comp_only2(self):
        """Test all= string"""
        param = 'all='
        self.parser_test(param, {'all': (None, None)})

    def test_complete1(self):
        """Test all=file:min string"""
        param = 'all=file:min'
        self.parser_test(param, {'all': ('file', 'min')})

    def test_complete2(self):
        """Test all=file:min: string"""
        param = 'all=file:min'
        self.parser_test(param, {'all': ('file', 'min')})

    def test_complete3(self):
        """Test all=file:min string"""
        param = 'all=file:min'
        self.parser_test(param, {'all': ('file', 'min')})

    def test_multiple1(self):
        """Test ops=file:min,http=file:min string"""
        param = 'ops=file:min,http=file:min'
        self.parser_test(param, {'ops': ('file', 'min'),
                                 'http': ('file', 'min')})

    def test_multiple2(self):
        """Test ops=file:min,http=file:min string"""
        param = 'ops=file:min,http='
        self.parser_test(param, {'ops': ('file', 'min'),
                                 'http': (None, None)})


class TestLogParseErrors(BaseLoggingTests):
    """ Test errors on the parse"""
    def parser_error_test(self, param):
        """Test for exception"""
        try:
            # pylint: disable=protected-access
            PywbemLoggers._parse_log_specs(param)
            self.fail('Param should generate exception %s' % param)
        except ValueError:
            pass

    def test_to_many_params(self):
        """ test all=file:min:junk string """
        param = "all=file:min:junk"
        self.parser_error_test(param)

    def test_empty(self):
        param = ""
        self.parser_error_test(param)


class TestLoggerCreate(BaseLoggingTests):
    """ Test the PywbemLoggers.create_logger method."""
    def test_create_single_logger1(self):
        """
        Create a simple logger
        """
        PywbemLoggers.create_logger('ops', 'file',
                                    log_filename=TEST_OUTPUT_LOG,
                                    log_detail_level='min')

        if VERBOSE:
            print('pywbem_loggers dict %s' % PywbemLoggers.loggers)
        expected_result = \
            {'pywbem.ops': ('min', 'file', TEST_OUTPUT_LOG)}

        # test getting from logger variable
        self.assertEqual(PywbemLoggers.loggers, expected_result)

        # test use of __repr__
        expected_result = 'PywbemLoggers(%s)' % expected_result
        self.assertEqual(('%r' % PywbemLoggers), expected_result)

    def test_create_single_logger2(self):
        """
        Create a simple logger from detailed parameter input
        """
        PywbemLoggers.create_logger('http', 'file',
                                    log_filename=TEST_OUTPUT_LOG,
                                    log_detail_level='min')

        if VERBOSE:
            print('pywbem_loggers dict %s' % PywbemLoggers.loggers)
        expected_result = \
            {'pywbem.http': ('min', 'file', TEST_OUTPUT_LOG)}

        self.assertEqual(PywbemLoggers.loggers, expected_result,
                         'Actual %s, Expected %s' % (PywbemLoggers.loggers,
                                                     expected_result))

    def test_create_single_logger3(self):
        """
        Create a simple logger from detailed parameter input
        """
        PywbemLoggers.create_logger('http', 'stderr',
                                    log_filename=None,
                                    log_detail_level='min')

        if VERBOSE:
            print('pywbem_loggers dict %s' % PywbemLoggers.loggers)
        expected_result = \
            {'pywbem.http': ('min', 'stderr', None)}

        self.assertEqual(PywbemLoggers.loggers, expected_result,
                         'Actual %s, Expected %s' % (PywbemLoggers.loggers,
                                                     expected_result))

    def test_create_single_logger4(self):
        """
        Create a simple logger from detailed parameter input
        """
        PywbemLoggers.create_logger('all', 'stderr',
                                    log_filename=None,
                                    log_detail_level='min')

        if VERBOSE:
            print('pywbem_loggers dict %s' % PywbemLoggers.loggers)
        expected_result = \
            {'pywbem.http': ('min', 'stderr', None),
             'pywbem.ops': ('min', 'stderr', None)}

        self.assertEqual(PywbemLoggers.loggers, expected_result)


class TestLoggerCreateErrors(BaseLoggingTests):
    """Test errors in the LoggerCreate Function"""

    def test_create_single_logger1(self):
        """
        Create a simple logger from detailed parameter input
        """
        try:
            PywbemLoggers.create_logger('httpx', 'stderr',
                                        log_filename=None,
                                        log_detail_level='min')
            self.fail('Exception expected')
        except ValueError as ve:
            if VERBOSE:
                print('ve %s' % ve)

    def test_create_single_logger2(self):
        """
        Create a simple logger from detailed parameter input
        """
        try:
            PywbemLoggers.create_logger('http', 'stderrblah',
                                        log_filename=None,
                                        log_detail_level='min')
            self.fail('Exception expected')
        except ValueError as ve:
            if VERBOSE:
                print('ve %s' % ve)

    def test_create_single_logger4(self):
        """
        Create a simple logger from detailed parameter input
        """
        try:
            PywbemLoggers.create_logger('http', 'stderr',
                                        log_filename=None,
                                        log_detail_level='mi')
            self.fail('Exception expected')
        except ValueError as ve:
            if VERBOSE:
                print('ve %s' % ve)

    def test_create_single_logger5(self):
        """
        Create a simple logger from detailed parameter input
        """
        try:
            PywbemLoggers.create_logger('http', 'file',
                                        log_filename=None,
                                        log_detail_level='mi')
            self.fail('Exception expected')
        except ValueError as ve:
            if VERBOSE:
                print('ve %s' % ve)


class TestLoggersCreate(BaseLoggingTests):
    """
    Tests to create loggers using the PywbemLogger class and the
    method create_loggers that creates logger definitions from
    an input string
    """
    def valid_loggers_create(self, input_str, expected_result,
                             log_filename=None):
        """Common test to do the create loggers and test result."""
        PywbemLoggers.create_loggers(input_str, log_filename)
        self.assertEqual(PywbemLoggers.loggers, expected_result)
        # TODO add test
        # for name in PywbemLoggers.loggers:
        #    print(PywbemLoggers.get_logger_info(name))

    def test_create_logger(self):
        """
        Create a simple logger
        """
        test_input = 'ops=file:min,http=file:min'

        expected_result = \
            {'pywbem.http': ('min', 'file', TEST_OUTPUT_LOG),
             'pywbem.ops': ('min', 'file', TEST_OUTPUT_LOG)}
        self.valid_loggers_create(test_input, expected_result,
                                  log_filename=TEST_OUTPUT_LOG)

    def test_create_loggers1(self):
        """
        Create a simple logger
        """
        test_input = 'all=file:min'
        expected_result = \
            {'pywbem.http': ('min', 'file', TEST_OUTPUT_LOG),
             'pywbem.ops': ('min', 'file', TEST_OUTPUT_LOG)}

        self.valid_loggers_create(test_input, expected_result,
                                  log_filename=TEST_OUTPUT_LOG)

    def test_create_loggers2(self):
        """
        Create a simple logger
        """
        test_input = 'all=stderr:all'
        expected_result = \
            {'pywbem.http': ('all', 'stderr', None),
             'pywbem.ops': ('all', 'stderr', None)}

        self.valid_loggers_create(test_input, expected_result)

    def test_get_logger_default(self):
        """ Test the get_logger function."""
        logger = get_logger(LOG_OPS_CALLS_NAME)
        self.assertEqual(len(logger.handlers), 1)
        log_info = PywbemLoggers.get_logger_info(LOG_OPS_CALLS_NAME)
        self.assertEqual(log_info[2], 'none')
        self.assertEqual(log_info[0], 'min')

    def test_get_logger_invalid(self):
        """ Test the get_logger function."""
        try:
            get_logger('pywbem.blah')
            self.fail('Expected exception for invalid log name')
        except ValueError:
            pass


class TestLoggerOutput(BaseLoggingTests):
    """Test output from logging"""

    @log_capture()
    def test_log_output(self, l):  # pylint: disable=blacklisted-name
        test_input = 'all=file:all'

        print('log filename %s' % TEST_OUTPUT_LOG)
        PywbemLoggers.create_loggers(test_input, TEST_OUTPUT_LOG)

        my_logger = get_logger(LOG_OPS_CALLS_NAME)

        self.assertNotEqual(my_logger, None,
                            'Valid named logger %s expected.'
                            % LOG_OPS_CALLS_NAME)
        # for name in PywbemLoggers.loggers:
        #    print(PywbemLoggers.get_logger_info(name))
        max_size = 1000
        result = 'This is fake return data'
        return_name = 'Return'
        if max_size and len(repr(result)) > max_size:
            result = '{:.{sz}s}...' \
                .format(repr(result), sz=max_size)
        else:
            result = '%s' % repr(result)

        my_logger.debug('%s: %s: %s', return_name, 'FakeMethodName', result)

        l.check(('pywbem.ops', 'DEBUG',
                 "Return: FakeMethodName: 'This is fake return data'"))


if __name__ == '__main__':
    unittest.main()
