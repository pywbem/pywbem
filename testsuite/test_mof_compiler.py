#!/usr/bin/env python
#

from __future__ import print_function, absolute_import

import sys
import os
from time import time
from zipfile import ZipFile
from tempfile import TemporaryFile
import unittest

import six
if six.PY2:
    # pylint: disable=wrong-import-order
    from urllib2 import urlopen
else:
    # pylint: disable=wrong-import-order
    from urllib.request import urlopen

from ply import lex

from pywbem.cim_operations import CIMError
from pywbem.mof_compiler import MOFCompiler, MOFWBEMConnection, MOFParseError
from pywbem.cim_constants import *
from pywbem import mof_compiler

## Constants
NAME_SPACE = 'root/test'

SCRIPT_DIR = os.path.dirname(__file__)
SCHEMA_DIR = os.path.join(SCRIPT_DIR, 'schema')

# Change the MOF_URL and CIM_SCHEMA_MOF when new schema is used.
# Also, manually delete schema dir.
MOF_URL = 'http://www.dmtf.org/standards/cim/cim_schema_v2450/' \
         'cim_schema_2.45.0Final-MOFs.zip'
CIM_SCHEMA_MOF = 'cim_schema_2.45.0.mof'

def setUpModule():

    if not os.path.isdir(SCHEMA_DIR):

        print("\nDownloading CIM Schema into %s ..." % SCHEMA_DIR)

        os.mkdir(SCHEMA_DIR)

        mofbname = MOF_URL.split('/')[-1]

        tfo = TemporaryFile()
        ufo = urlopen(MOF_URL)
        clen = int(ufo.info().get('Content-Length'))
        offset = 0
        ppct = -1
        for data in ufo:
            offset += len(data)
            pct = 100*offset/clen
            if pct > ppct:
                ppct = pct
                sys.stdout.write('\rDownloading %s: %d%% ' % (mofbname, pct))
                sys.stdout.flush()
            tfo.write(data)
        tfo.seek(0)
        print('')

        zf = ZipFile(tfo, 'r')
        nlist = zf.namelist()
        for i in range(0, len(nlist)):
            sys.stdout.write('\rUnpacking %s: %d%% ' % (mofbname,
                                                        100*(i+1)/len(nlist)))
            sys.stdout.flush()
            file_ = nlist[i]
            dfile = os.path.join(SCHEMA_DIR, file_)
            if dfile[-1] == '/':
                if not os.path.exists(dfile):
                    os.mkdir(dfile)
            else:
                fo = open(dfile, 'w+b')
                fo.write(zf.read(file_))
                fo.close()
        tfo.close()
        print('')


class MOFTest(unittest.TestCase):
    """A base class that creates a MOF compiler instance"""

    def setUp(self):
        """Create the MOF compiler."""

        def moflog(msg):
            print(msg, file=self.logfile)
        moflog_file = os.path.join(SCRIPT_DIR, 'moflog.txt')
        self.logfile = open(moflog_file, 'w')
        self.mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=[SCHEMA_DIR], verbose=False,
            log_func=moflog)


class TestFullSchema(MOFTest):

    def test_all(self):
        t = time()
        self.mofcomp.compile_file(
            os.path.join(SCHEMA_DIR, CIM_SCHEMA_MOF), NAME_SPACE)
        print('elapsed: %f  ' % (time() - t))
        # TODO The number of qualifiers and classes is version dependent
        self.assertEqual(len(self.mofcomp.handle.qualifiers[NAME_SPACE]),
                         70)
        self.assertEqual(len(self.mofcomp.handle.classes[NAME_SPACE]),
                         1621)

class TestAliases(MOFTest):

    def test_all(self):
        self.mofcomp.compile_file(
            os.path.join(SCRIPT_DIR, 'test.mof'), NAME_SPACE)

class TestSchemaError(MOFTest):

    def test_all(self):
        self.mofcomp.parser.search_paths = []
        try:
            self.mofcomp.compile_file(os.path.join(SCHEMA_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_FAILED)
            self.assertEqual(ce.file_line[0],
                             os.path.join(SCHEMA_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'))
            if ce.file_line[1] != 2:
                print('assert {}'.format(ce.file_line))
            self.assertEqual(ce.file_line[1], 2)

        self.mofcomp.compile_file(os.path.join(SCHEMA_DIR,
                                               'qualifiers.mof'),
                                  NAME_SPACE)
        try:
            self.mofcomp.compile_file(os.path.join(SCHEMA_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_INVALID_SUPERCLASS)
            self.assertEqual(ce.file_line[0],
                             os.path.join(
                                 SCHEMA_DIR,
                                 'System',
                                 'CIM_ComputerSystem.mof'))
            # TODO The following is cim version dependent.
            if ce.file_line[1] != 179:
                print('assertEqual {} line {}'.format(ce,
                                                      ce.file_line[1]))
            self.assertEqual(ce.file_line[1], 179)

class TestSchemaSearch(MOFTest):

    def test_all(self):
        self.mofcomp.compile_file(os.path.join(SCHEMA_DIR,
                                               'System',
                                               'CIM_ComputerSystem.mof'),
                                  NAME_SPACE)
        ccs = self.mofcomp.handle.GetClass(
            'CIM_ComputerSystem',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(ccs.properties['RequestedState'].type, 'uint16')
        self.assertEqual(ccs.properties['Dedicated'].type, 'uint16')
        cele = self.mofcomp.handle.GetClass(
            'CIM_EnabledLogicalElement',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(cele.properties['RequestedState'].type, 'uint16')


class TestParseError(MOFTest):

    def test_all(self):
        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error01.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 16)
            self.assertEqual(pe.context[5][1:5], '^^^^')
            self.assertEqual(pe.context[4][1:5], 'size')

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error02.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 6)
            self.assertEqual(pe.context[5][7:13], '^^^^^^')
            self.assertEqual(pe.context[4][7:13], 'weight')

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error03.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 24)
            self.assertEqual(pe.context[5][53], '^')
            self.assertEqual(pe.context[4][53], '}')

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error04.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(str(pe), 'Unexpected end of file')

class TestRefs(MOFTest):

    def test_all(self):
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_refs.mof'),
                                  NAME_SPACE)

# pylint: disable=too-few-public-methods
class LexErrorToken(lex.LexToken):
    """Class indicating an expected LEX error."""
    # Like lex.LexToken, we set its instance variables from outside
    pass

def _test_log(msg):
    """Our log function when testing."""
    pass

class BaseTestLexer(unittest.TestCase):
    """Base class for testcases just for the lexical analyzer."""

    def setUp(self):
        self.mofcomp = MOFCompiler(handle=None, log_func=_test_log)
        self.lexer = self.mofcomp.lexer
        self.last_error_t = None  # saves 't' arg of t_error()

        def test_t_error(t):
            """Our replacement for t_error() when testing."""
            self.last_error_t = t
            self.saved_t_error(t)

        self.saved_t_error = mof_compiler.t_error
        mof_compiler.t_error = test_t_error

    def tearDown(self):
        mof_compiler.t_error = self.saved_t_error

    @staticmethod
    def lex_token(type, value, lineno, lexpos):
        """Return an expected LexToken."""
        tok = lex.LexToken()
        tok.type = type
        tok.value = value
        tok.lineno = lineno
        tok.lexpos = lexpos
        return tok

    @staticmethod
    def lex_error(value, lineno, lexpos):
        """Return an expected LEX error."""
        tok = LexErrorToken()
        tok.type = None
        tok.value = value
        tok.lineno = lineno
        tok.lexpos = lexpos
        return tok

    def debug_data(self, input_data):
        """For debugging testcases: Print input data and its tokens."""
        print("debug_data: input_data=<%s>" % input_data)
        self.lexer.input(input_data)
        while True:
            tok = self.lexer.token()
            if not tok:
                break  # No more input
            print("debug_data: token=<%s>" % tok)

    def run_assert_lexer(self, input_data, exp_tokens):
        """Run lexer and assert results."""

        # Supply the lexer with input
        self.lexer.input(input_data)

        token_iter = iter(exp_tokens)
        while True:

            # Get next parsed token from lexer,
            # returns None if exhausted
            act_token = self.lexer.token()

            try:
                exp_token = six.next(token_iter)
            except StopIteration:
                exp_token = None  # indicate tokens exhausted

            if act_token is None and exp_token is None:
                break  # successfully came to the end
            elif act_token is None and exp_token is not None:
                self.fail("Not enough tokens found, expected: %r" % exp_token)
            elif act_token is not None and exp_token is None:
                self.fail("Too many tokens found: %r" % act_token)
            else:
                # We have both an expected and an actual token
                if isinstance(exp_token, LexErrorToken):
                    # We expect an error
                    if self.last_error_t is None:
                        self.fail("t_error() was not called as expected, " \
                                  "actual token: %r" % act_token)
                    else:
                        self.assertTrue(
                            self.last_error_t.type == exp_token.type and \
                            self.last_error_t.value == exp_token.value,
                            "t_error() was called with an unexpected " \
                            "token: %r (expected: %r)" % \
                            (self.last_error_t, exp_token))
                else:
                    # We do not expect an error
                    if self.last_error_t is not None:
                        self.fail(
                            "t_error() was unexpectedly called with " \
                            "token: %r" % self.last_error_t)
                    else:
                        self.assertTrue(
                            act_token.type == exp_token.type,
                            "Unexpected token type: %s (expected: %s) " \
                            "in token: %r" % \
                            (act_token.type, exp_token.type, act_token))
                        self.assertTrue(
                            act_token.value == exp_token.value,
                            "Unexpected token value: %s (expected: %s) " \
                            "in token: %r" % \
                            (act_token.value, exp_token.value, act_token))
                        self.assertTrue(
                            act_token.lineno == exp_token.lineno,
                            "Unexpected token lineno: %s (expected: %s) " \
                            "in token: %r" % \
                            (act_token.lineno, exp_token.lineno, act_token))
                        self.assertTrue(
                            act_token.lexpos == exp_token.lexpos,
                            "Unexpected token lexpos: %s (expected: %s) " \
                            "in token: %r" % \
                            (act_token.lexpos, exp_token.lexpos, act_token))

class TestLexerSimple(BaseTestLexer):
    """Simple testcases for the lexical analyzer."""

    def test_empty(self):
        """Test an empty string."""
        self.run_assert_lexer("", [])

    def test_simple(self):
        """Test a simple list of tokens."""
        input_data = """a 42"""
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('decimalValue', '42', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

class TestLexerNumber(BaseTestLexer):
    """Number testcases for the lexical analyzer."""

    # Decimal numbers

    def test_decimal_0(self):
        """Test a decimal number 0."""
        input_data = """0"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_plus_0(self):
        """Test a decimal number +0."""
        input_data = """+0"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_minus_0(self):
        """Test a decimal number -0."""
        input_data = """-0"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small(self):
        """Test a small decimal number."""
        input_data = """12345"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_plus(self):
        """Test a small decimal number with +."""
        input_data = """+12345"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_minus(self):
        """Test a small decimal number with -."""
        input_data = """-12345"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_long(self):
        """Test a decimal number that is long."""
        input_data = """12345678901234567890"""
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Binary numbers

    def test_binary_0b(self):
        """Test a binary number 0b."""
        input_data = """0b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_0B(self):
        """Test a binary number 0B (upper case B)."""
        input_data = """0B"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small(self):
        """Test a small binary number."""
        input_data = """101b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_plus(self):
        """Test a small binary number with +."""
        input_data = """+1011b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_minus(self):
        """Test a small binary number with -."""
        input_data = """-1011b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_long(self):
        """Test a binary number that is long."""
        input_data = """1011001101001011101101101010101011001011111001101b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzero(self):
        """Test a binary number with a leading zero."""
        input_data = """01b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzeros(self):
        """Test a binary number with two leading zeros."""
        input_data = """001b"""
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Octal numbers

    def test_octal_00(self):
        """Test octal number 00."""
        input_data = """00"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_01(self):
        """Test octal number 01."""
        input_data = """01"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small(self):
        """Test a small octal number."""
        input_data = """0101"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_plus(self):
        """Test a small octal number with +."""
        input_data = """+01011"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_minus(self):
        """Test a small octal number with -."""
        input_data = """-01011"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_long(self):
        """Test an octal number that is long."""
        input_data = """07051604302011021104151151610403031021011271071701"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_leadingzeros(self):
        """Test an octal number with two leading zeros."""
        input_data = """001"""
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Floating point numbers

    def test_float_dot0(self):
        """Test a float number '.0'."""
        input_data = """.0"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_0dot0(self):
        """Test a float number '0.0'."""
        input_data = """0.0"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_plus_0dot0(self):
        """Test a float number '+0.0'."""
        input_data = """+0.0"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_minus_0dot0(self):
        """Test a float number '-0.0'."""
        input_data = """-0.0"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small(self):
        """Test a small float number."""
        input_data = """123.45"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_plus(self):
        """Test a small float number with +."""
        input_data = """+123.45"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_minus(self):
        """Test a small float number with -."""
        input_data = """-123.45"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_long(self):
        """Test a float number that is long."""
        input_data = """1.2345678901234567890"""
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Errors

    def test_error_09(self):
        """Test '09' (decimal: no leading zeros; octal: digit out of range)."""
        input_data = """09"""
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_008(self):
        """Test '008' (decimal: no leading zeros; octal: digit out of range)."""
        input_data = """008"""
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_2b(self):
        """Test '2b' (decimal: b means binary; binary: digit out of range)."""
        input_data = """2b"""
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_02B(self):
        """Test '02B' (decimal: B means binary; binary: digit out of range;
        octal: B means binary)."""
        input_data = """02B"""
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_0dot(self):
        """Test a float number '0.' (not allowed)."""
        input_data = """0."""
        exp_tokens = [
            # TODO: The current floatValue regexp does not match, so
            # it treats this as decimal. Improve the handling of this.
            self.lex_token('decimalValue', '0', 1, 0),
            # TODO: This testcase succeeds without any expected token for the
            # '.'. Find out why.
        ]
        self.run_assert_lexer(input_data, exp_tokens)


if __name__ == '__main__':
    unittest.main()
