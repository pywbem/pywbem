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
import io
import re
import logging

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import pytest

# logging_tree is a useful tool to understand what the logging
# configuraiton produces.  It is not normally installed in pywbem but simply
# documented here for anyone changing these tests. You must manually install
# it with pip. It displays a tree of loggers with pertinent information about
# each logger.
# from logging_tree import printout
# To use the tool just set a line to printout() where you want to see what
# loggers exist

from testfixtures import LogCapture, compare, TempDirectory

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, \
    ConnectionError  # noqa: E402 pylint: disable=redefined-builtin
from pywbem._logging import configure_loggers_from_string, configure_logger, \
    LOGGER_API_CALLS_NAME, LOGGER_HTTP_NAME  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


VERBOSE = False

# Location of any test scripts
TEST_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_logging.log'
TEST_OUTPUT_LOG = '%s/%s' % (TEST_DIR, LOG_FILE_NAME)


@pytest.fixture(autouse=True)
def tmp_dir():
    with TempDirectory() as tmpdir:
        yield tmpdir


# Used in place of log_capture decorator with pytest since the
# test_fixtures log_capture decorator does not work with pytest
@pytest.fixture(autouse=True)
def log_capture():
    with LogCapture() as lc:
        yield lc


class TestLoggingConfigure(object):
    """Base class for logging unit tests"""

    @classmethod
    def setup_class(cls):
        """Setup that is run before each test method."""
        # pylint: disable=protected-access
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
                assert 'Input error. log_name %s ' % log_name

            # TODO compare detail_level

            compare(logger.level, 10)
            if logger.handlers[0]:
                assert len(logger.handlers) == 1
                if log_dest == 'file':
                    assert isinstance(logger.handlers[0],
                                      logging.FileHandler) is True
                    assert log_filename is not None
                elif log_dest == 'stderr':
                    assert isinstance(logger.handlers[0],
                                      logging.StreamHandler) is True
            else:
                assert False, 'No logger defined for test'

    @pytest.mark.parametrize(
        "log_name", ['api', 'http', 'all']
    )
    @pytest.mark.parametrize(
        "log_dest, detail_level, log_filename, exp_except",
        [
            ['file', 'all', TEST_OUTPUT_LOG, None],
            ['stderr', 'all', TEST_OUTPUT_LOG, None],
            ['file', 'paths', TEST_OUTPUT_LOG, None],
            ['stderr', 'paths', TEST_OUTPUT_LOG, None],
            ['file', 10, TEST_OUTPUT_LOG, None],
            ['stderr', 10, TEST_OUTPUT_LOG, None],
            ['file', 'summary', TEST_OUTPUT_LOG, None],
            ['stderr', 'summary', TEST_OUTPUT_LOG, None],
            ['stderr', None, TEST_OUTPUT_LOG, None],
            # Error tests
            ['blah', 'all', TEST_OUTPUT_LOG, ValueError],
            ['file', 'blah', TEST_OUTPUT_LOG, ValueError],
            ['file', -9, TEST_OUTPUT_LOG, ValueError],
            ['file', [-9], TEST_OUTPUT_LOG, ValueError],
            ['file', 'all', None, ValueError],
        ]
    )
    def test_configure_logger(self, log_name, log_dest, detail_level,
                              log_filename, exp_except):
        """
        Test variations of the configure_logger method including errors.
        """
        if exp_except:
            with pytest.raises(exp_except):
                configure_logger(log_name, log_dest=log_dest,
                                 detail_level=detail_level,
                                 log_filename=log_filename)
        else:
            configure_logger(log_name, log_dest=log_dest,
                             detail_level=detail_level,
                             log_filename=log_filename)

            self.logger_validate(log_name, log_dest, detail_level,
                                 log_filename=log_filename)

            # Disable logger to get log file closed.
            configure_logger(log_name, log_dest='off')

    def test_configure_logger_nameerror(self):
        """
        Test that invalid logger name parameter generates exception. The
        previous test handles valid names
        """
        with pytest.raises(ValueError):
            configure_logger("BadLogName", log_dest='stderr',
                             detail_level="all")


TESTCASES_TEST_LOGGERS_FROM_STRING = [
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * param: String to be tested.
    #   * expected_result: Dictionary of expected results
    #   * log_file: log_file for stderr tests or `None`.
    #   * connection_defined - `None` or predefined connection
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning types, or `None`
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "'Test all' string",
        dict(
            param='all',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('all', 'all')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test all=' string",
        dict(
            param='all=',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('all', 'all')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test all=file' string",
        dict(
            param='all=file',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('all', 'all')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test all=file:summary' string",
        dict(
            param='all=file:summary',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('summary', 'summary')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test all=file:paths' string",
        dict(
            param='all=file:paths',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('path', 'path')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test all=file;10' string",
        dict(
            param='all=file:10',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('10', '10')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test all=file,http=file:all' string",
        dict(
            param='api=file,http=file:all',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.FileHandler),
                             'detail': ('all', 'all')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    (
        "'Test api=file,http=stderr",
        dict(
            param='api=file,http=stderr',
            expected_result={'level': (10, 10),
                             'handler': (logging.FileHandler,
                                         logging.StreamHandler),
                             'detail': ('all', 'all')},
            log_file='Blah.log',
            connection_defined=None
        ),
        None, None, True
    ),
    # Error tests
    (
        "Test invalid '",
        dict(
            param='all=blah',
            expected_result={},
            log_file='Blah.log',
            connection_defined=None
        ),
        ValueError, None, True
    ),
    (
        "Test invalid 'api=stderr,https=blah''",
        dict(
            param='all=blah',
            expected_result={},
            log_file='Blah.log',
            connection_defined=None
        ),
        ValueError, None, True
    ),
    (
        "Test invalid 'all=file:all:junk'",
        dict(
            param='all=file:all:junk',
            expected_result={},
            log_file='Blah.log',
            connection_defined=None
        ),
        ValueError, None, True
    ),
    (
        "Test invalid 'all=file' with no log file",
        dict(
            param='all=file:all:junk',
            expected_result={},
            log_file=None,
            connection_defined=None
        ),
        ValueError, None, True
    ),
    (
        "Test invalid 'all=blah'",
        dict(
            param='',
            expected_result={},
            log_file='Blah.log',
            connection_defined=None
        ),
        ValueError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TEST_LOGGERS_FROM_STRING)
@simplified_test_function
def test_loggers_from_string(testcase, param, expected_result, log_file,
                             connection_defined):
    """ Test of logging configuration from String input"""
    # pylint: disable=protected-access

    # Logging handlers are static.  We must clear them between tests
    # Remove any handlers from loggers for this test
    WBEMConnection._reset_logging_config()  # pylint: disable=protected-access
    api_logger = logging.getLogger(LOGGER_API_CALLS_NAME)
    api_logger.handlers = []
    http_logger = logging.getLogger(LOGGER_HTTP_NAME)
    http_logger.handlers = []

    if connection_defined:  # pylint: disable=no-else-raise
        conn = WBEMConnection('http:/blah')
        raise AssertionError('TODO: Test with connections not yet implemented')
    else:
        conn = True  # for all future connections

    configure_loggers_from_string(param, log_filename=log_file,
                                  connection=conn, propagate=True)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

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
            assert len(api_logger.handlers) == 1
            assert isinstance(api_logger.handlers[0], handler[0])
        if handler[1]:
            assert len(http_logger.handlers) == 1
            assert isinstance(http_logger.handlers[0], handler[1])

    if 'detail' in expected_result:
        exp_detail_levels = expected_result['detail']
        if connection_defined:  # pylint: disable=no-else-raise
            # TODO add test for when connection param exists
            # need to get to recorder and test detail level
            raise AssertionError(
                'TODO: Test with connections not yet implemented')
        else:
            detail_levels = WBEMConnection._log_detail_levels
            assert detail_levels['api'], exp_detail_levels[0] is True
            assert detail_levels['http'], exp_detail_levels[1]

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


class BaseLoggingExecutionTests(object):
    """Base class for logging execution tests"""

    def setup_method(self):
        """Setup that is run before each test method."""
        # pylint: disable=protected-access
        WBEMConnection._reset_logging_config()
        configure_loggers_from_string(
            'all=file', TEST_OUTPUT_LOG, propagate=True, connection=True)
        # pylint: disable=attribute-defined-outside-init
        self.logger = logging.getLogger(LOGGER_API_CALLS_NAME)
        assert self.logger is not None

    def teardown_method(self):
        LogCapture.uninstall_all()
        configure_loggers_from_string('all=off', connection=True)
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class TestLoggerOutput(BaseLoggingExecutionTests):
    """Test output from logging"""

    def test_log_output_faked(self, log_capture):
        # pylint: disable=redefined-outer-name
        """
        Test faked log output.
        """
        log_data = 'This is fake log data'

        self.logger.debug(log_data)

        log_capture.check(('pywbem.api', 'DEBUG', log_data))

    def test_log_output_conn(self):
        # pylint: disable=redefined-outer-name
        """
        Test log output of creating a WBEMConnection object and executing
        a GetQualifier operation that fails.
        """

        url = 'http://dummy:5988'  # File URL to get quick result
        conn = WBEMConnection(url)
        try:
            conn.GetQualifier('Association')
        except ConnectionError:
            pass
        else:
            raise AssertionError("ConnectionError exception not raised")

        exp_line_patterns = [
            r".*-{0}\..*-Connection:.* WBEMConnection\(url='{1}'".
            format(LOGGER_API_CALLS_NAME, url),
            r".*-{0}\..*-Request:.* GetQualifier\(QualifierName='Association'".
            format(LOGGER_API_CALLS_NAME),
            r".*-{0}\..*-Request:.* POST /cimom .* CIMMethod:'GetQualifier'".
            format(LOGGER_HTTP_NAME),
            r".*-{0}\..*-Exception:.* GetQualifier.*ConnectionError".
            format(LOGGER_API_CALLS_NAME),
        ]

        with io.open(TEST_OUTPUT_LOG, "r", encoding='utf-8') as log_fp:
            log_lines = log_fp.readlines()
        assert len(log_lines) == len(exp_line_patterns)
        for i, pattern in enumerate(exp_line_patterns):
            assert re.match(pattern, log_lines[i])


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

        with io.open(logger_filename, encoding='utf-8') as logger_fp:
            logger_line = logger_fp.read()
        assert re.match(r'.*-%s\..*-Connection:' % logger_name, logger_line)

        with io.open(pkg_filename, encoding='utf-8') as pkg_fp:
            pkg_line = pkg_fp.read()
        if propagate:
            assert re.match(r'.*-pywbem.*-Connection:', pkg_line)
        else:
            assert pkg_line == ''

        # Clean up the Python logging configuration
        configure_logger(short_name, connection=False)
