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
Unit test logging functionality in _logging.py and
the WBEMConnection.configure_logger methods

"""

from __future__ import absolute_import, print_function

import os
import logging

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import unittest

# logging_tree is a useful tool to understand what the logging
# configuraiton produces.  It is not normally installed in pywbem but simply
# documented here for anyone changing these tests. You must manually install
# it with pip. It displays a tree of loggers with pertinent information about
# each logger.
# from logging_tree import printout
# To use the tool just set a line to printout() where you want to see what
# loggers exist

from testfixtures import LogCapture, log_capture, compare

from pywbem import WBEMConnection
from pywbem._logging import configure_loggers_from_string, \
    LOGGER_API_CALLS_NAME, LOGGER_HTTP_NAME

VERBOSE = False

# Location of any test scripts for testing wbemcli.py
SCRIPT_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_logging.log'
TEST_OUTPUT_LOG = '%s/%s' % (SCRIPT_DIR, LOG_FILE_NAME)


class BaseLoggingTest(unittest.TestCase):
    """
    Methods required by all tests
    """
    @staticmethod
    def _get_logger(logger_name):
        """Duplicate method local to recorder"""
        logger = logging.getLogger(logger_name)
        if logger_name != '' and not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger


class UnitLoggingTests(BaseLoggingTest):
    """Base class for logging unit tests"""

    def logger_validate(self, log_name, log_dest, detail_level,
                        log_filename=None):
        """
        Test for correct definition of one logger. Creates the logger and
        tests the logger parameters against expected results. This does not
        create any logs.
        """
        if log_name == 'all':
            self.logger_validate('api', log_dest, detail_level,
                                 log_filename=log_filename)
            self.logger_validate('http', log_dest, detail_level,
                                 log_filename=log_filename)

        else:
            if log_name == 'api':
                logger = self._get_logger(LOGGER_API_CALLS_NAME)
            elif log_name == 'http':
                logger = self._get_logger(LOGGER_HTTP_NAME)
            else:
                self.fail('Input error. log_name %s ' % log_name)

            # TODO compare detail_level

            compare(logger.level, 10)
            if logger.handlers[0]:
                self.assertEqual(len(logger.handlers), 1)
                if log_dest == 'file':
                    self.assertTrue(isinstance(logger.handlers[0],
                                               logging.FileHandler))
                    self.assertTrue(log_filename is not None)
                elif log_dest == 'stderr':
                    self.assertTrue(isinstance(logger.handlers[0],
                                               logging.StreamHandler))
            else:
                self.fail('No logger defined')

    def configure_logger_test(self, log_name, log_dest=None, detail_level=None,
                              log_filename=None, error=None):
        """
        Unified test function for the configure_logger function
        """
        if error:
            try:
                WBEMConnection.configure_logger(log_name, log_dest=log_dest,
                                                detail_level=detail_level,
                                                log_filename=log_filename)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            WBEMConnection.configure_logger(log_name, log_dest=log_dest,
                                            detail_level=detail_level,
                                            log_filename=log_filename)

            self.logger_validate(log_name, log_dest, detail_level,
                                 log_filename=log_filename)

    def loggers_from_string_test(self, param, expected_result, log_file=None,
                                 connection_defined=False):
        """ Common test for successful parsing"""
        # pylint: disable=protected-access

        # logging handlers are static.  We must clear them between tests
        # Remove any handlers from loggers for this test
        api_logger = self._get_logger(LOGGER_API_CALLS_NAME)
        api_logger.handlers = []
        http_logger = self._get_logger(LOGGER_HTTP_NAME)
        http_logger.handlers = []

        # TODO for test below not yet implemented
        # if connection_defined:
        #    conn = WBEMConnection('http:/blah')

        if expected_result == 'error':
            try:
                configure_loggers_from_string(param, log_filename=log_file)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            configure_loggers_from_string(param, log_filename=log_file)

            api_logger = self._get_logger(LOGGER_API_CALLS_NAME)
            http_logger = self._get_logger(LOGGER_HTTP_NAME)
            if 'level' in expected_result:
                level = expected_result['level']
                if level[0]:
                    compare(api_logger.level, level[0])

                if level[1]:
                    compare(http_logger.level, level[1])
            if 'handler' in expected_result:
                handler = expected_result['handler']

                if handler[0]:
                    self.assertEqual(len(api_logger.handlers), 1)
                    self.assertTrue(isinstance(api_logger.handlers[0],
                                               handler[0]))
                if handler[1]:
                    self.assertEqual(len(http_logger.handlers), 1)
                    self.assertTrue(isinstance(http_logger.handlers[0],
                                               handler[1]))

            if 'detail' in expected_result:
                detail_level = expected_result['detail']
                if connection_defined:
                    # TODO add test for when connection param exists
                    # need to get to recorder and test detail level
                    pass
                    # print(conn)
                else:
                    if detail_level[0]:
                        details = WBEMConnection._log_config_dict
                        self.assertTrue(details['api']) == detail_level[0]

        # remove handlers from our loggers.
        for h in api_logger.handlers:
            api_logger.removeHandler(h)
            h.flush()
            h.close()
        for h in http_logger.handlers:
            http_logger.removeHandler(h)
            h.flush()
            h.close()

        # Close log file
        if log_file:
            if os.path.exists(log_file):
                os.remove(log_file)


class TestLoggersFromString(UnitLoggingTests):
    """
    Test the configure_loggers_from_string and WBEMConnection.configure_logger
    functions. Some of the logging configuration methods are in WBEMConnection
    """

    def test_comp_only(self):
        """'Test all' string"""
        self.loggers_from_string_test('all', {'level': (0, 0),
                                              'handler': (logging.NullHandler,
                                                          logging.NullHandler),
                                              'detail': (None, None)})

    def test_comp_only2(self):
        """'Test all=' string"""
        param = 'all='
        self.loggers_from_string_test(param, {'level': (0, 0),
                                              'handler': (logging.NullHandler,
                                                          logging.NullHandler)})

    def test_complete1(self):
        """Test all=file string"""
        param = 'all=file'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler)},
                                      log_file='blah.log')

    def test_complete2(self):
        """Test all=file:summary string"""
        param = 'all=file:summary'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler),
                                              'detail': ('summary', 'summary')},

                                      log_file='blah.log')

    def test_complete3(self):
        """Test all=file:summary string"""
        param = 'all=file:10'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler),
                                              'detail': (10, 10)},

                                      log_file='blah.log')

    def test_multiple1(self):
        """Test api=file:min,http=file:all string"""
        param = 'api=file,http=file:all'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler)},
                                      log_file='blah.log')

    def test_multiple2(self):
        """Test api=file:min,http=file:min string"""
        param = 'api=file,http=stderr'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler':
                                              (logging.FileHandler,
                                               logging.StreamHandler)},
                                      log_file='blah.log')

    def test_invalid_logname(self):
        """Test for exception, log name invalid.  'blah' """
        param = 'blah'
        self.loggers_from_string_test(param, 'error')

    def test_to_many_params(self):
        """ test all=file:junk string """
        param = "all=file:all:junk"
        self.loggers_from_string_test(param, 'error')

    def test_empty(self):
        param = ""
        self.loggers_from_string_test(param, 'error')


class TestDefineLogger(UnitLoggingTests):
    """ Test the configure_logger method."""

    def test_configue_single_logger1(self):
        """
        Create a simple logger
        """
        self.configure_logger_test('api', 'file', detail_level='all',
                                   log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger2(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.configure_logger_test('http', 'file', detail_level='all',
                                   log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger3(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.configure_logger_test('http', 'stderr', detail_level='all',
                                   log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger4(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.configure_logger_test('all', 'stderr', detail_level='all',
                                   log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger5(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.configure_logger_test('all', 'stderr', detail_level='all',
                                   log_filename=TEST_OUTPUT_LOG)

    def test_create_single_loggerEr1(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.configure_logger_test('api', 'blah', detail_level='all',
                                   error=True)
        self.configure_logger_test('http', 'blah', detail_level='all',
                                   error=True)
        self.configure_logger_test('api', 'blah', detail_level='al',
                                   error=True)
        self.configure_logger_test('http', 'blah', detail_level='al',
                                   error=True)


class BaseLoggingExecutionTests(BaseLoggingTest):
    """Base class for logging unit tests"""

    def tearDown(self):
        LogCapture.uninstall_all()
        logging.shutdown()
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class TestLoggerOutput(BaseLoggingExecutionTests):
    """Test output from logging"""

    @log_capture()
    def test_log_output(self, l):  # pylint: disable=blacklisted-name
        test_input = 'all=file'

        configure_loggers_from_string(test_input, TEST_OUTPUT_LOG)

        my_logger = self._get_logger(LOGGER_API_CALLS_NAME)

        self.assertNotEqual(my_logger, None,
                            'Valid named logger %s expected.'
                            % LOGGER_API_CALLS_NAME)

        max_size = 1000
        result = 'This is fake return data'
        return_name = 'Return'
        if max_size and len(repr(result)) > max_size:
            result = '{:.{sz}s}...' \
                .format(repr(result), sz=max_size)
        else:
            result = '%s' % repr(result)

        my_logger.debug('%s: %s: %s', return_name, 'FakeMethodName', result)

        l.check(('pywbem.api', 'DEBUG',
                 "Return: FakeMethodName: 'This is fake return data'"))


if __name__ == '__main__':
    unittest.main()
