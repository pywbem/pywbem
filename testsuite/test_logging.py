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

# The folowing is a useful tool if you have to sort out what the logging
# configuraiton produces.  It is not normallyt installed in pywbem but simply
# documented here for anyone changing these tests.  It displays a tree
# of loggers with pertinent information about each logger.
# from logging_tree import printout
# To use the tool just set a line to printout() where you want to see what
# loggers exist
from testfixtures import LogCapture, log_capture, compare

from pywbem import LOG_OPS_CALLS_NAME, LOG_HTTP_NAME
from pywbem._logging import get_logger, define_logger, \
    define_loggers_from_string

VERBOSE = False

# Location of any test scripts for testing wbemcli.py
SCRIPT_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_logging.log'
TEST_OUTPUT_LOG = '%s/%s' % (SCRIPT_DIR, LOG_FILE_NAME)


class UnitLoggingTests(unittest.TestCase):
    """Base class for logging unit tests"""
    def single_logger_validate(self, log_component, log_dest, log_filename):
        """Test for correct definition of one logger
        """
        if log_component == 'ops':
            logger = get_logger(LOG_OPS_CALLS_NAME)
        elif log_component == 'http':
            logger = get_logger(LOG_HTTP_NAME)
        else:
            self.fail('Input error. log_component %s ' % log_component)

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

    def define_logger_test(self, log_component, log_dest=None,
                           log_filename=None, error=None):
        """Unified test funciton for the define_logger function
        """
        if error:
            try:
                define_logger(log_component, log_dest=log_dest,
                              log_filename=log_filename)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            define_logger(log_component, log_dest=log_dest,
                          log_filename=log_filename)

            if log_component == 'all':
                for op in ['ops', 'http']:
                    self.single_logger_validate(op, log_dest, log_filename)

    def loggers_test(self, param, expected_result, log_file=None):
        """ Common test for successful parsing"""
        # pylint: disable=protected-access
        if expected_result == 'error':
            try:
                define_loggers_from_string(param, log_filename=log_file)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            define_loggers_from_string(param, log_filename=log_file)

            ops_logger = get_logger(LOG_OPS_CALLS_NAME)
            http_logger = get_logger(LOG_HTTP_NAME)
            if 'level' in expected_result:
                level = expected_result['level']
                if level[0]:
                    compare(ops_logger.level, level[0])

                if level[1]:
                    compare(http_logger.level, level[1])
            if 'handler' in expected_result:
                handler = expected_result['handler']
                if handler[0]:
                    self.assertEqual(len(ops_logger.handlers), 1)
                    self.assertTrue(isinstance(ops_logger.handlers[0], handler))
                    # compare(ops_logger.handlers[0], 'logging.StreamHandler')


class TestLoggersDefine(UnitLoggingTests):
    """
    Test the define_loggers_from_string and define_logger functions
    """

    def test_comp_only(self):
        """Test all string"""
        self.loggers_test('all', {'level': (10, 10),
                                  'handler': (logging.NullHandler,
                                              logging.NullHandler)})

    def test_comp_only2(self):
        """Test all= string"""
        param = 'all='
        self.loggers_test(param, {'level': (10, 10),
                                  'handler': (logging.NullHandler,
                                              logging.NullHandler)})

    def test_complete1(self):
        """Test all=filestring"""
        param = 'all=file'
        self.loggers_test(param, {'level': (10, 10),
                                  'handler': (logging.FileHandler,
                                              logging.FileHandler)},
                          log_file='blah.log')

    def test_multiple1(self):
        """Test ops=file:min,http=file:min string"""
        param = 'ops=file,http=file'
        self.loggers_test(param, {'level': (10, 10),
                                  'handler': (logging.FileHandler,
                                              logging.FileHandler)},
                          log_file='blah.log')

    def test_multiple2(self):
        """Test ops=file:min,http=file:min string"""
        param = 'ops=file,http=stderr'
        self.loggers_test(param, {'level': (10, 10),
                                  'handler': (logging.FileHandler,
                                              logging.StreamHandler)},
                          log_file='blah.log')

    def parser_error_test(self):
        """Test for exception"""
        try:
            # pylint: disable=protected-access
            param = 'blah'
            self.loggers_test(param, 'error')
            self.fail('Param should generate exception %s' % param)
        except ValueError:
            pass

    def test_to_many_params(self):
        """ test all=file:junk string """
        param = "all=file:min:junk"
        self.loggers_test(param, 'error')

    def test_empty(self):
        param = ""
        self.loggers_test(param, 'error')


class TestDefineLogger(UnitLoggingTests):
    """ Test the define_logger method."""

    def test_define_single_logger1(self):
        """
        Create a simple logger
        """
        self.define_logger_test('ops', 'file', log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger2(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('http', 'file', log_filename=TEST_OUTPUT_LOG)

    def test_create_single_logger3(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('http', 'stderr', log_filename=None)

    def test_create_single_logger4(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('all', 'stderr', log_filename=None)

    def test_create_single_loggerEr1(self):
        """
        Create a simple logger from detailed parameter input
        """
        self.define_logger_test('all', 'stderr', log_filename=None, )


class TestLoggerCreateErrors(UnitLoggingTests):
    """Test errors in the LoggerCreate Function"""

    def test_create_single_logger1(self):
        """
        Create a simple logger from detailed parameter input
        """
        try:
            define_logger('httpx', 'stderr', log_filename=None)
            self.fail('Exception expected')
        except ValueError as ve:
            if VERBOSE:
                print('ve %s' % ve)

    def test_create_single_logger2(self):
        """
        Create a simple logger from detailed parameter input
        """
        try:
            define_logger('http', 'stderrblah', log_filename=None)
            self.fail('Exception expected')
        except ValueError as ve:
            if VERBOSE:
                print('ve %s' % ve)


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

        my_logger = get_logger(LOG_OPS_CALLS_NAME)

        self.assertNotEqual(my_logger, None,
                            'Valid named logger %s expected.'
                            % LOG_OPS_CALLS_NAME)

        max_size = 1000
        result = 'This is fake return data'
        return_name = 'Return'
        if max_size and len(repr(result)) > max_size:
            result = '{:.{sz}s}...' \
                .format(repr(result), sz=max_size)
        else:
            result = '%s' % repr(result)

        my_logger.debug('%s: %s: %s', return_name, 'FakeMethodName', result)

        # print(l)

        l.check(('pywbem.ops', 'DEBUG',
                 "Return: FakeMethodName: 'This is fake return data'"))


if __name__ == '__main__':
    unittest.main()
