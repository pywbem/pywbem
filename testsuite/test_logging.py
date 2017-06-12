#!/usr/bin/env python

# Copyright 2017 Karl Schopmeyer
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

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import unittest

from pywbem import PywbemLoggers


class BaseLoggingTests(unittest.TestCase):
    """Base class for logging unit tests"""
    def setUp(self):
        pass

    def tearDown(self):
        pass


class LogParseTests(BaseLoggingTests):
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
        self.parser_test(param, {'all': (None, None, None)})

    def test_comp_only2(self):
        """Test all= string"""
        param = 'all='
        self.parser_test(param, {'all': (None, None, None)})

    def test_complete1(self):
        """Test all=file:min:debug string"""
        param = 'all=file:min:debug'
        self.parser_test(param, {'all': ('file', 'min', 'debug')})

    def test_complete2(self):
        """Test all=file:min: string"""
        param = 'all=file:min:'
        self.parser_test(param, {'all': ('file', 'min', None)})

    def test_complete3(self):
        """Test all=file:min string"""
        param = 'all=file:min'
        self.parser_test(param, {'all': ('file', 'min', None)})

    def test_complete4(self):
        """Test all=::debug string"""
        param = 'all=::debug'
        self.parser_test(param, {'all': (None, None, 'debug')})

    def test_complete5(self):
        """Test all=::debug string"""
        param = 'all=:min:'
        self.parser_test(param, {'all': (None, 'min', None)})

    def test_multiple1(self):
        """Test ops=file:min,http=file:min:debug string"""
        param = 'ops=file:min,http=file:min:debug'
        self.parser_test(param, {'ops': ('file', 'min', None),
                                 'http': ('file', 'min', 'debug')})

    def test_multiple2(self):
        """Test ops=file:min,http=file:min:debug string"""
        param = 'ops=file:min,http='
        self.parser_test(param, {'ops': ('file', 'min', None),
                                 'http': (None, None, None)})


class LogParseTestErrors(BaseLoggingTests):
    """ Test errors on the parse"""
    def parser_error_test(self, param):
        """Test for exception"""
        try:
            # pylint: disable=protected-access
            PywbemLoggers._parse_log_specs(param)
            self.fail('param should generate exception %s' % param)
        except ValueError:
            pass

    def test_to_many_params(self):
        """ test all=file:min:debug:junk string """
        param = "all=file:min:debug:junk"
        self.parser_error_test(param)

    def test_empty(self):
        param = ""
        self.parser_error_test(param)


class LoggerCreateTests(BaseLoggingTests):
    """ Test the PywbemLoggers.create_logger method."""
    def test_create_single_logger(self):
        """
        Create a simple logger
        """
        PywbemLoggers.create_logger('ops', 'file',
                                    log_filename='loggingtest.log',
                                    log_level='debug')

        print('pywbem_loggers dict %s' % PywbemLoggers.loggers)

        # TODO add test    


class LoggersCreateTests(BaseLoggingTests):
    """
    Tests to create loggers using the PywbemLogger class
    """
    def valid_loggers_create(self, input_str, expected_result):
        """Common test to do the create loggers and test result."""
        PywbemLoggers.create_loggers(input_str)
        print('pywbem_loggers dict %s' % PywbemLoggers.loggers)
        # TODO add test
        for name in PywbemLoggers.loggers:
            print(PywbemLoggers.get_logger_info(name))


    def test_create_loggers(self):
        """
        Create a simple logger
        """
        test_input = 'ops=file:min:debug,http=file:min:debug'

        self.valid_loggers_create(test_input, None)


if __name__ == '__main__':
    unittest.main()
