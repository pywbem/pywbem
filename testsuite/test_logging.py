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
from pywbem._logging import get_logger, define_loggers_from_string, \
    LOG_API_CALLS_NAME, LOG_HTTP_NAME

VERBOSE = False

# Location of any test scripts for testing wbemcli.py
SCRIPT_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_logging.log'
TEST_OUTPUT_LOG = '%s/%s' % (SCRIPT_DIR, LOG_FILE_NAME)


class UnitLoggingTests(unittest.TestCase):
    """Base class for logging unit tests"""

    def logger_validate(self, log_name, log_dest, detail_level,
                        log_filename=None):
        """Test for correct definition of one logger
        """
        if log_name == 'api':
            logger = get_logger(LOG_API_CALLS_NAME)
        elif log_name == 'http':
            logger = get_logger(LOG_HTTP_NAME)
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

    def define_logger_test(self, log_name, log_dest=None, detail_level=None,
                           log_filename=None, error=None):
        """
        Unified test function for the define_logger function
        """
        if error:
            try:
                if log_name == 'api':
                    WBEMConnection.configure_api_logger(
                        log_dest=log_dest, detail_level=detail_level,
                        log_filename=log_filename)
                    self.fail('Exception expected')
                elif log_name == 'http':

                    WBEMConnection.configure_http_logger(
                        log_dest=log_dest, detail_level=detail_level,
                        log_filename=log_filename)
                    self.fail('Exception expected')
                elif log_name == 'app':
                    WBEMConnection.configure_all_loggers(
                        log_dest=log_dest, detail_level=detail_level,
                        log_filename=log_filename)
                    self.fail('Exception expected')
                else:
                    self.fail('Invalid log_name %s' % log_name)
            except ValueError:
                pass
        else:
            if log_name == 'api':
                WBEMConnection.configure_api_logger(
                    log_dest=log_dest, detail_level=detail_level,
                    log_filename=log_filename)
                self.logger_validate(log_name, log_dest, detail_level,
                                     log_filename=log_filename)
            elif log_name == 'http':
                WBEMConnection.configure_http_logger(
                    log_dest=log_dest, detail_level=detail_level,
                    log_filename=log_filename)
                self.logger_validate(log_name, log_dest, detail_level,
                                     log_filename=log_filename)

            elif log_name == 'all':
                WBEMConnection.configure_all_loggers(
                    log_dest=log_dest, detail_level=detail_level,
                    log_filename=log_filename)
                self.logger_validate('api', log_dest, detail_level,
                                     log_filename=log_filename)
                self.logger_validate('http', log_dest, detail_level,
                                     log_filename=log_filename)

            else:
                self.fail('Invalid log_name %s' % log_name)

    def loggers_from_string_test(self, param, expected_result, log_file=None,
                                 connection_defined=False):
        """ Common test for successful parsing"""
        # pylint: disable=protected-access

        # logging handlers are static.  We must clear them between tests
        # Remove any handlers from loggers for this test
        api_logger = get_logger(LOG_API_CALLS_NAME)
        api_logger.handlers = []
        http_logger = get_logger(LOG_HTTP_NAME)
        http_logger.handlers = []

        if connection_defined:
            conn = WBEMConnection('http:/blah')

        if expected_result == 'error':
            try:
                define_loggers_from_string(param, log_filename=log_file)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            define_loggers_from_string(param, log_filename=log_file)

            api_logger = get_logger(LOG_API_CALLS_NAME)
            http_logger = get_logger(LOG_HTTP_NAME)
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
                    print(conn)
                else:
                    if detail_level[0]:
                        details = WBEMConnection._log_config_dict
                        self.assertTrue(details['api']) == detail_level[0]

        # try to remove any created log file.
        if log_file:
            if os.path.exists(log_file):
                os.remove(log_file)


class TestLoggersFromString(UnitLoggingTests):
    """
    Test the define_loggers_from_string and define_logger functions. Some of
    the logging configuration methods are in WBEMConnection
    """

    def test_comp_only(self):
        """Test all string"""
        self.loggers_from_string_test('all', {'level': (0, 0),
                                              'handler': (logging.NullHandler,
                                                          logging.NullHandler),
                                              'detail': (None, None)})

    def test_comp_only2(self):
        """Test all= string"""
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
    """ Test the define_logger method."""

    def test_define_single_logger1(self):
        """
        Create a simple logger
        """
        self.define_logger_test('api', 'file', detail_level='all',
                                log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger2(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('http', 'file', detail_level='all',
                                log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger3(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('http', 'stderr', detail_level='all',
                                log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger4(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('all', 'stderr', detail_level='all',
                                log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger5(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('all', 'stderr', detail_level='all',
                                log_filename=TEST_OUTPUT_LOG)

    def test_create_single_loggerEr1(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('api', 'blah', detail_level='all', error=True)
        self.define_logger_test('http', 'blah', detail_level='all', error=True)
        self.define_logger_test('api', 'blah', detail_level='al', error=True)
        self.define_logger_test('http', 'blah', detail_level='al', error=True)


class BaseLoggingTests(unittest.TestCase):
    """Base class for logging unit tests"""

    def tearDown(self):
        LogCapture.uninstall_all()
        logging.shutdown()
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class TestLoggerOutput(BaseLoggingTests):
    """Test output from logging"""

    @log_capture()
    def test_log_output(self, l):  # pylint: disable=blacklisted-name
        test_input = 'all=file'

        define_loggers_from_string(test_input, TEST_OUTPUT_LOG)

        my_logger = get_logger(LOG_API_CALLS_NAME)

        self.assertNotEqual(my_logger, None,
                            'Valid named logger %s expected.'
                            % LOG_API_CALLS_NAME)

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
