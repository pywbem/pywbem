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
import re
import logging

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import unittest
import pytest

# logging_tree is a useful tool to understand what the logging
# configuraiton produces.  It is not normally installed in pywbem but simply
# documented here for anyone changing these tests. You must manually install
# it with pip. It displays a tree of loggers with pertinent information about
# each logger.
# from logging_tree import printout
# To use the tool just set a line to printout() where you want to see what
# loggers exist

from testfixtures import LogCapture, log_capture, compare, TempDirectory
from pywbem import WBEMConnection
from pywbem._logging import configure_loggers_from_string, configure_logger, \
    LOGGER_API_CALLS_NAME, LOGGER_HTTP_NAME

VERBOSE = False

# Location of any test scripts for testing wbemcli.py
TEST_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_logging.log'
TEST_OUTPUT_LOG = '%s/%s' % (TEST_DIR, LOG_FILE_NAME)


@pytest.fixture(autouse=True)
def tmp_dir():
    with TempDirectory() as tmpdir:
        yield tmpdir


class BaseLoggingTest(unittest.TestCase):
    """
    Methods required by all tests
    """


class UnitLoggingTests(BaseLoggingTest):
    """Base class for logging unit tests"""

    def setUp(self):
        """Setup that is run before each test method."""
        WBEMConnection._reset_logging_config()

    def logger_validate(self, log_name, log_dest, detail_level,
                        log_filename=None):
        """
        Test for correct definition of one logger. Creates the logger and
        tests the logger parameters against expected results. This does not
        create any logs.
        """
        if log_name == 'all':
            self.logger_validate('api', log_dest, detail_level=detail_level,
                                 log_filename=log_filename)
            self.logger_validate('http', log_dest, detail_level,
                                 log_filename=log_filename)

        else:
            if log_name == 'api':
                logger = logging.getLogger(LOGGER_API_CALLS_NAME)
            elif log_name == 'http':
                logger = logging.getLogger(LOGGER_HTTP_NAME)
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
                configure_logger(log_name, log_dest=log_dest,
                                 detail_level=detail_level,
                                 log_filename=log_filename)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            configure_logger(log_name, log_dest=log_dest,
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
        api_logger = logging.getLogger(LOGGER_API_CALLS_NAME)
        api_logger.handlers = []
        http_logger = logging.getLogger(LOGGER_HTTP_NAME)
        http_logger.handlers = []

        if connection_defined:
            self.fail('TODO: Test with connections not yet implemented')
            conn = WBEMConnection('http:/blah')
        else:
            conn = True  # for all future connections

        if expected_result == 'error':
            try:
                configure_loggers_from_string(param, log_filename=log_file,
                                              connection=conn, propagate=True)
                self.fail('Exception expected')
            except ValueError:
                pass
        else:
            configure_loggers_from_string(param, log_filename=log_file,
                                          connection=conn, propagate=True)

            api_logger = logging.getLogger(LOGGER_API_CALLS_NAME)
            http_logger = logging.getLogger(LOGGER_HTTP_NAME)

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
                exp_detail_levels = expected_result['detail']
                if connection_defined:
                    # TODO add test for when connection param exists
                    # need to get to recorder and test detail level
                    self.fail('TODO: Test with connections not yet implemented')
                else:
                    detail_levels = WBEMConnection._log_detail_levels
                    self.assertTrue(detail_levels['api'], exp_detail_levels[0])
                    self.assertTrue(detail_levels['http'], exp_detail_levels[1])

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
    Test the configure_loggers_from_string and configure_logger
    functions. Some of the logging configuration methods are in WBEMConnection
    """

    def test_comp_only(self):
        """'Test all' string"""
        param = 'all'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler),
                                              'detail': ('all', 'all')},
                                      log_file='blah.log')

    def test_comp_only2(self):
        """'Test all=' string"""
        param = 'all='
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler),
                                              'detail': ('all', 'all')},
                                      log_file='blah.log')

    def test_complete1(self):
        """Test all=file string"""
        param = 'all=file'
        self.loggers_from_string_test(param, {'level': (10, 10),
                                              'handler': (logging.FileHandler,
                                                          logging.FileHandler),
                                              'detail': ('all', 'all')},
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

    def setUp(self):
        """Setup that is run before each test method."""
        WBEMConnection._reset_logging_config()

    def tearDown(self):
        LogCapture.uninstall_all()
        logging.shutdown()
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class TestLoggerOutput(BaseLoggingExecutionTests):
    """Test output from logging"""

    @log_capture()
    def test_log_output(self, lc):
        test_input = 'all=file'

        configure_loggers_from_string(
            test_input, TEST_OUTPUT_LOG, propagate=True)

        my_logger = logging.getLogger(LOGGER_API_CALLS_NAME)

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

        lc.check(('pywbem.api', 'DEBUG',
                  "Return: FakeMethodName: 'This is fake return data'"))


class TestLoggerPropagate(object):
    # pylint: disable=too-few-public-methods
    """Test logging with propagate parameter variations"""

    @pytest.mark.parametrize(
        "propagate", (True, False)
    )
    @pytest.mark.parametrize(
        "logger_names", (
            ('api', 'pywbem.api'),
            # http logger does not log WBEMConnection
        )
    )
    def test_logger_propagate(self, tmp_dir, logger_names, propagate):
        # pylint: disable=redefined-outer-name
        """Test log event propagation behavior."""

        short_name, logger_name = logger_names

        # The testing approach is to log to files and check their contents.
        # Neither LogCapture nor OutputCapture seemed to work with pytest.
        logger_filename = os.path.join(tmp_dir.path, 'pywbem.xxx.log')
        pkg_filename = os.path.join(tmp_dir.path, 'pywbem.log')

        # Create a log handler on the 'pywbem.<xxx>' logger to be tested
        configure_logger(short_name, log_dest='file',
                         log_filename=logger_filename,
                         detail_level='all', connection=True,
                         propagate=propagate)

        # Create a log handler on the 'pywbem' logger (parent)
        pkg_logger = logging.getLogger('pywbem')
        pkg_handler = logging.FileHandler(pkg_filename, encoding="UTF-8")
        pkg_handler.setLevel(logging.DEBUG)
        pkg_formatter = logging.Formatter('%(asctime)s-%(name)s-%(message)s')
        pkg_handler.setFormatter(pkg_formatter)
        pkg_logger.addHandler(pkg_handler)

        # Create a log event
        WBEMConnection('bla')

        # Verify the 'propagate' attribute of the logger to be tested
        logger = logging.getLogger(logger_name)
        assert logger.propagate == propagate

        for h in logger.handlers + pkg_logger.handlers:
            try:
                h.flush()
                h.close()
            except AttributeError:
                pass

        pkg_logger.removeHandler(pkg_handler)

        with open(logger_filename) as logger_fp:
            logger_line = logger_fp.read()
        assert re.match(r'.*-%s\..*-Connection:' % logger_name, logger_line)

        with open(pkg_filename) as pkg_fp:
            pkg_line = pkg_fp.read()
        if propagate:
            assert re.match(r'.*-pywbem.*-Connection:', pkg_line)
        else:
            assert pkg_line == ''


if __name__ == '__main__':
    unittest.main()
