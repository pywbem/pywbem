#!/usr/bin/env python
#

"""
Unittest functions in cim_operations.
"""

from __future__ import print_function, absolute_import

import pytest

from pywbem.cim_operations import check_utf8_xml_chars, ParseError, \
    WBEMConnection, CIMError

from pywbem._recorder import LogOperationRecorder

from pywbem._recorder import TestClientRecorder as MyTestClientRecorder

#################################################################
# Test check_utf8_xml_chars function
#################################################################


# pylint: disable=invalid-name, too-few-public-methods
class TestCheckUtf8XmlChars(object):
    """Test various inputs to the check_utf8_xml_chars function"""

    VERBOSE = False

    def _run_single(self, utf8_xml, expected_ok):
        """Run single test from test_all. Executes the check...
           function and catches exceptions
        """
        if self.VERBOSE:
            print('utf8_xml %s type %s ' % (utf8_xml, type(utf8_xml)))
        try:
            check_utf8_xml_chars(utf8_xml, "Test XML")
        except ParseError as exc:
            if self.VERBOSE:
                print("Verify manually: Input XML: %r, ParseError: %s" %
                      (utf8_xml, exc))
            assert expected_ok is False
        else:
            assert expected_ok

    def test_all(self):
        """ Test cases. Each case tests a particular utf8 xml string"""

        # good cases
        self._run_single(b'<V>a</V>', True)
        self._run_single(b'<V>a\tb\nc\rd</V>', True)
        self._run_single(b'<V>a\x09b\x0Ac\x0Dd</V>', True)
        self._run_single(b'<V>a\xCD\x90b</V>', True)             # U+350
        self._run_single(b'<V>a\xE2\x80\x93b</V>', True)         # U+2013
        self._run_single(b'<V>a\xF0\x90\x84\xA2b</V>', True)     # U+10122

        # invalid XML characters
        if self.VERBOSE:
            print("From here on, the only expected exception is ParseError "
                  "for invalid XML characters...")
        self._run_single(b'<V>a\bb</V>', False)
        self._run_single(b'<V>a\x08b</V>', False)
        self._run_single(b'<V>a\x00b</V>', False)
        self._run_single(b'<V>a\x01b</V>', False)
        self._run_single(b'<V>a\x1Ab</V>', False)
        self._run_single(b'<V>a\x1Ab\x1Fc</V>', False)

        # correctly encoded but ill-formed UTF-8
        if self.VERBOSE:
            print("From here on, the only expected exception is ParseError "
                  "for ill-formed UTF-8 Byte sequences...")
        # combo of U+D800,U+DD22:
        self._run_single(b'<V>a\xED\xA0\x80\xED\xB4\xA2b</V>', False)
        # combo of U+D800,U+DD22 and combo of U+D800,U+DD23:
        # pylint: disable=line-too-long
        self._run_single(
            b'<V>a\xED\xA0\x80\xED\xB4\xA2b\xED\xA0\x80\xED\xB4\xA3</V>',
            False)

        # incorrectly encoded UTF-8
        if self.VERBOSE:
            print("From here on, the only expected exception is ParseError "
                  "for invalid UTF-8 Byte sequences...")
        # incorrect 1-byte sequence:
        self._run_single(b'<V>a\x80b</V>', False)
        # 2-byte sequence with missing second byte:
        self._run_single(b'<V>a\xC0', False)
        # 2-byte sequence with incorrect 2nd byte
        self._run_single(b'<V>a\xC0b</V>', False)
        # 4-byte sequence with incorrect 3rd byte:
        self._run_single(b'<V>a\xF1\x80abc</V>', False)
        # 4-byte sequence with incorrect 3rd byte that is an incorr. new start:
        self._run_single(b'<V>a\xF1\x80\xFFbc</V>', False)
        # 4-byte sequence with incorrect 3rd byte that is an correct new start:
        self._run_single(b'<V>a\xF1\x80\xC2\x81c</V>', False)


class TestCreateConnection(object):
    """
    Test construction of WBEMConnection and those functions that do not
    depend on actually creating a connection
    """
    def test_connection_defaults(self):  # pylint: disable=no-self-use
        """Test creation of a connection with default constructor
           parameters.
        """
        conn = WBEMConnection('http://localhost')
        assert conn.url == 'http://localhost'
        assert conn.creds is None
        assert conn.x509 is None
        assert conn.use_pull_operations is False
        assert conn.stats_enabled is False

    def test_no_recorder(self):  # pylint: disable=no-self-use
        """Test creation of wbem connection with specific parameters"""
        creds = ('myname', 'mypw')
        x509 = {'cert_file': 'mycertfile.crt', 'key_file': 'mykeyfile.key'}
        conn = WBEMConnection('http://localhost', creds,
                              default_namespace='root/blah',
                              x509=x509,
                              use_pull_operations=True,
                              enable_stats=True)
        assert conn.url == 'http://localhost'
        assert conn.creds == creds
        assert conn.x509 == x509
        assert conn.stats_enabled is True
        assert conn.use_pull_operations is True

    def test_add_operation_recorder(self):  # pylint: disable=no-self-use
        """Test addition of an operation recorder"""
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder())
        # pylint: disable=protected-access
        assert len(conn._operation_recorders) == 1

    def test_add_operation_recorders(self):  # pylint: disable=no-self-use
        """Test addition of multiple operation recorders"""
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder())
        tcr_file = MyTestClientRecorder.open_file('blah.yaml', 'a')
        conn.add_operation_recorder(MyTestClientRecorder(tcr_file))
        # pylint: disable=protected-access
        assert len(conn._operation_recorders) == 2

    def test_add_same_twice(self):  # pylint: disable=no-self-use
        """ Test addition of same recorder twice"""
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder())
        # pylint: disable=protected-access
        assert len(conn._operation_recorders) == 1

        with pytest.raises(ValueError):
            conn.add_operation_recorder(LogOperationRecorder())


class TestGetRsltParams(object):
    """Test WBEMConnection._get_rslt_params method."""

    @pytest.mark.parametrize(
        'irval', [None, 'bla', [], {}])
    @pytest.mark.parametrize(
        # enumctxt input, eos input, expected_eos, exception_expected
        'ec, eos, eos_exp, exc_exp', [
            # following are successul returns
            [u'contextblah', u'False', False, False],   # normal enumctxt rtn
            ["", u'True', True, False],              # eos true, enmctxt empty
            [None, u'True', True, False],              # eos true, enmctxt None
            [u'contextblah', u'True', True, False],    # eos tru, cts with value
            # following are exceptions
            [None, None, None, True],       # fail,no values in eos or enumctxt
            [None, u'False', None, True],   # fail,no value in ec and eos False
        ]
    )
    # pylint: disable=no-self-use
    def test_with_params(self, irval, ec, eos, eos_exp, exc_exp):
        """
        Test combminations of IRETURNVALUE, EOS and EnumerationContext for
        both good and fail responses.
        """
        result = [
            (u'IRETURNVALUE', {}, irval),
            (u'EnumerationContext', None, ec),
            (u'EndOfSequence', None, eos)
        ]

        if exc_exp:
            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                result = WBEMConnection._get_rslt_params(result, 'root/blah')

            exc = exec_info.value
            assert exc.status_code_name == 'CIM_ERR_INVALID_PARAMETER'

        else:
            # pylint: disable=protected-access
            result = WBEMConnection._get_rslt_params(result, 'root/blah')
            # the _get_rslt_params method sets context to None if eos True
            ecs = None if eos_exp is True else (ec, 'root/blah')
            assert result == (irval, eos_exp, ecs)

    # pylint: disable=no-self-use
    def test_missing(self):
        """
        Test both Enum context and EndOfSequence completely missing.
        Generates exception
        """
        result = [
            (u'IRETURNVALUE', {}, {})
        ]
        with pytest.raises(CIMError) as exec_info:
            # pylint: disable=protected-access
            result = WBEMConnection._get_rslt_params(result, 'namespace')

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_INVALID_PARAMETER'
