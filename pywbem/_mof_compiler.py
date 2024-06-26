#
# (C) Copyright 2006-2007 Novell, Inc.
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
# Author: Bart Whiteley <bwhiteley suse.de>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

"""
The language in which CIM classes, CIM Instances, etc. are specified, is
called `MOF` (for Managed Object Format). It is defined in :term:`DSP0004`.

MOF compilers take MOF files as input, compile them and use the result
(CIM classes, instances, and/or qualifier declarations) to update a target
CIM repository. The repository may initially be empty, or may contain CIM
classes, instances, and/or qualifier declarations that are used to resolve
dependencies the new MOF compilation may have.

The pywbem package includes a MOF compiler that is provided in two forms:

* as an API (described in this chapter)
* as a command (described in section :ref:`mof_compiler`)

The pywbem MOF compiler will compile MOF files whose syntax complies with
:term:`DSP0004`, with some limitations:

1. Although there is no formal keyword list of illegal words
   for property/parameter.etc. names , there is a list of mof syntax tokens
   in :term:`DSP0004` section A.3.  Generally these should not be used as
   property names.  The pywbem MOF compiler largely enforces this so that words
   like 'indication' are not allowed as property/parameter/etc. names.

2. The key properties of instances with aliases must be initialized in the
   instance specification, or their default values must be non-NULL.
   (See `pywbem issue #1079 <https://github.com/pywbem/pywbem/issues/1079>`_).

3. An alias must be defined before it is used. In :term:`DSP0004`, no such
   requirement is documented.
   (See `pywbem issue #1079 <https://github.com/pywbem/pywbem/issues/1079>`_).

4. The namespace pragma only accepts CIM namespace name and not full
   CIM namespace path as defined in DSP0004. If the host component is part
   of the namespace name in a namespace pragma, the compiler generates an
   exception.

The MOF compiler API provides for invoking the MOF compiler programmatically.
It consists of the following parts, which are described in the remaining
sections of this chapter:

* :ref:`MOFCompiler Class` - Describes the :class:`~pywbem.MOFCompiler`
  class, which allows invoking the MOF compiler programmatically.

* :ref:`Repository connections` - Describes the
  :class:`~pywbem.BaseRepositoryConnection` class that defines
  the interface for connecting to a CIM repository. This is an extension point
  where users can implement a CIM repository for use by the MOF compiler.

* :ref:`Exceptions <MOF compiler exceptions>` - Describes the exceptions
  that can be raised by the MOF compiler API.
"""

import sys
import os
import io
import re
import tempfile
import warnings
from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from ply import yacc, lex

from ._vendor.nocaselist import NocaseList
from ._nocasedict import NocaseDict
from ._cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, cimvalue
from ._cim_operations import WBEMConnection
from ._server import WBEMServer
from ._cim_constants import CIM_ERR_NOT_FOUND, CIM_ERR_FAILED, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_NAMESPACE, \
    CIM_ERR_INVALID_SUPERCLASS, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_NOT_SUPPORTED
from ._exceptions import Error, CIMError
from ._utils import _format, _ensure_unicode
from ._warnings import ToleratedSchemaIssueWarning

__all__ = ['MOFCompileError', 'MOFParseError', 'MOFDependencyError',
           'MOFRepositoryError', 'MOFCompiler', 'BaseRepositoryConnection',
           'MOFWBEMConnection']

# The following pylint is applied for the complete file because invalid
# names are used throughout the file and about 200 flags generated if
# this is not applied and at least some # may be part of ply rules.

# pylint: disable=invalid-name

_optimize = 1
_tabmodule = '_mofparsetab'
_lextab = '_moflextab'
_module = sys.modules.get('pywbem._mof_compiler', None)

# Directory for _tabmodule and _lextab
_tabdir = os.path.dirname(os.path.abspath(__file__))

# wbem_uri Namespace path regex used to test pragma namespace
WBEM_URI_NAMESPACEPATH_REGEXP = re.compile(
    r'^(?:([\w\-]+):)?'  # namespace type (URI scheme)
    r'(?://([\w.:@\[\]]*))?'  # authority (host)
    r'(?:/|^/?)(\w+(?:/\w+)*)$',  # namespace name (leading slash optional)
    flags=re.UNICODE)

# -----------------------------------------------------------------------------
#
# IMPORTANT NOTE:
#
# This MOF compiler implementation is based on the PLY Python package.
# This module here contains LEX & YACC rules in docstrings of its functions.
# The formatting of these docstrings is critical in that it defines the parser
# functionality. These docstrings are processed by the LEX & YACC in PLY.
# Changing the strings or even the formatting breaks the PLY rule generation!
#
# In the YACC of PLY 2.3 (included in pywbem up to 0.7), the requirement was
# that each choice of a YACC rule needed to be on a single line, and the first
# choice needed to be on the same line as the rule name. Not sure what the
# requirements of the current PLY version are.
#
# The LEX token functions and strings are all named "t_*".
# Note the order of LEX token processing, described in:
# https://www.dabeaz.com/ply/ply.html#ply_nn6
#
# The YACC parser functions are all named "p_*".
#
# -----------------------------------------------------------------------------

reserved = {
    'any': 'ANY',
    'as': 'AS',
    'association': 'ASSOCIATION',
    'class': 'CLASS',
    'disableoverride': 'DISABLEOVERRIDE',
    'boolean': 'DT_BOOL',
    'char16': 'DT_CHAR16',
    'datetime': 'DT_DATETIME',
    'pragma': 'PRAGMA',
    'real32': 'DT_REAL32',
    'real64': 'DT_REAL64',
    'sint16': 'DT_SINT16',
    'sint32': 'DT_SINT32',
    'sint64': 'DT_SINT64',
    'sint8': 'DT_SINT8',
    'string': 'DT_STR',
    'uint16': 'DT_UINT16',
    'uint32': 'DT_UINT32',
    'uint64': 'DT_UINT64',
    'uint8': 'DT_UINT8',
    'enableoverride': 'ENABLEOVERRIDE',
    'false': 'FALSE',
    'flavor': 'FLAVOR',
    'indication': 'INDICATION',
    'instance': 'INSTANCE',
    'method': 'METHOD',
    'null': 'NULL',
    'of': 'OF',
    'parameter': 'PARAMETER',
    'property': 'PROPERTY',
    'qualifier': 'QUALIFIER',
    'ref': 'REF',
    'reference': 'REFERENCE',
    'restricted': 'RESTRICTED',
    'schema': 'SCHEMA',
    'scope': 'SCOPE',
    'tosubclass': 'TOSUBCLASS',
    'toinstance': 'TOINSTANCE',
    'translatable': 'TRANSLATABLE',
    'true': 'TRUE',
    }  # noqa: E123

tokens = list(reserved.values()) + [
    'IDENTIFIER',
    'stringValue',
    'floatValue',
    'charValue',
    'binaryValue',
    'octalValue',
    'decimalValue',
    'hexValue',
]

literals = '#(){};[],$:='

# UTF-8 (from Unicode 4.0.0 standard):
# Table 3-6. Well-Formed UTF-8 Byte Sequences Code Points
# 1st Byte 2nd Byte 3rd Byte 4th Byte
# U+0000..U+007F     00..7F
# U+0080..U+07FF     C2..DF   80..BF
# U+0800..U+0FFF     E0       A0..BF   80..BF
# U+1000..U+CFFF     E1..EC   80..BF   80..BF
# U+D000..U+D7FF     ED       80..9F   80..BF
# U+E000..U+FFFF     EE..EF   80..BF   80..BF
# U+10000..U+3FFFF   F0       90..BF   80..BF   80..BF
# U+40000..U+FFFFF   F1..F3   80..BF   80..BF   80..BF
# U+100000..U+10FFFF F4       80..8F   80..BF   80..BF

utf8_2 = r'[\xC2-\xDF][\x80-\xBF]'
utf8_3_1 = r'\xE0[\xA0-\xBF][\x80-\xBF]'
utf8_3_2 = r'[\xE1-\xEC][\x80-\xBF][\x80-\xBF]'
utf8_3_3 = r'\xED[\x80-\x9F][\x80-\xBF]'
utf8_3_4 = r'[\xEE-\xEF][\x80-\xBF][\x80-\xBF]'
utf8_4_1 = r'\xF0[\x90-\xBF][\x80-\xBF][\x80-\xBF]'
utf8_4_2 = r'[\xF1-\xF3][\x80-\xBF][\x80-\xBF][\x80-\xBF]'
utf8_4_3 = r'\xF4[\x80-\x8F][\x80-\xBF][\x80-\xBF]'

utf8Char = (fr'({utf8_2})|({utf8_3_1})|({utf8_3_2})|({utf8_3_3})|({utf8_3_4})|'
            fr'({utf8_4_1})|({utf8_4_2})|({utf8_4_3})')


# pylint: disable=unused-argument
def t_COMMENT(t):
    r'//.*'
    return  # discard token


def t_MCOMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lineno += t.value.count('\n')
    return  # discard token

# These simple tokens must also be defined as functions, in order to control
# the order of evaluation.


def t_floatValue(t):
    r'[+-]?[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?'
    t.value = float(t.value)
    return t


def t_hexValue(t):
    r'[+-]?0[xX][0-9a-fA-F]+'
    t.value = int(t.value, 16)
    return t


def t_binaryValue(t):
    r'[+-]?[0-9]+[bB]'
    # We must match [0-9], and then check the validity of the binary number.
    # If we match [0-1], the invalid binary number "2b" would match
    # 'decimalValue' 2 and 'IDENTIFIER 'b'.
    if re.search(r'[2-9]', t.value) is not None:
        msg = _format("Invalid binary number {0!A}", t.value)
        t.lexer.last_msg = msg
        t.type = 'error'
        # Setting error causes the value to be automatically skipped
    else:
        t.value = int(t.value[0:-1], 2)
    return t


def t_octalValue(t):
    r'[+-]?0[0-9]+'
    # We must match [0-9], and then check the validity of the octal number.
    # If we match [0-7], the invalid octal number "08" would match
    # 'decimalValue' 0 and 'decimalValue' 8.
    if re.search(r'[8-9]', t.value) is not None:
        msg = _format("Invalid octal number {0!A}", t.value)
        t.lexer.last_msg = msg
        t.type = 'error'
        # Setting error causes the value to be automatically skipped
    else:
        t.value = int(t.value, 8)
    return t


# Matching for decimal must be at the end of the other numerics because of
# the 0. If not at the end, 0 would match at the begin of e.g. an octal value.
def t_decimalValue(t):
    r'[+-]?([1-9][0-9]*|0)'
    t.value = int(t.value)
    return t


simpleEscape = r"""[bfnrt'"\\]"""
hexEscape = r'[xX][0-9a-fA-F]{1,4}'
escapeSequence = fr'[\\](({simpleEscape})|({hexEscape}))'
cChar = fr"[^'\\\n\r]|({escapeSequence})"
sChar = fr'[^"\\\n\r]|({escapeSequence})'

charvalue_re = fr"'({cChar})'"


@lex.TOKEN(charvalue_re)
def t_charValue(t):  # pylint: disable=missing-docstring
    return t


stringvalue_re = fr'"({sChar})*"'


@lex.TOKEN(stringvalue_re)
def t_stringValue(t):  # pylint: disable=missing-docstring
    return t


identifier_re = fr'([a-zA-Z_]|({utf8Char}))([0-9a-zA-Z_]|({utf8Char}))*'


@lex.TOKEN(identifier_re)
def t_IDENTIFIER(t):  # pylint: disable=missing-docstring
    t.type = reserved.get(t.value.lower(), 'IDENTIFIER')
    return t


def t_newline(t):  # pylint: disable=missing-docstring
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.linestart = t.lexpos
    return  # discard token


t_ignore = ' \r\t'


def t_error(t):
    """ Lexer error callback from PLY Lexer with token in error.
    """
    msg = _format("Illegal character {0!A}", t.value[0])
    t.lexer.last_msg = msg
    t.lexer.skip(1)
    return t  # Return the error token for the YACC parser to handle


class MOFCompileError(Error):
    """
    Base class for exceptions indicating issues with compiling MOF.

    Derived from :exc:`~pywbem.Error`.
    """

    error_kind = "MOF compile error"

    # pylint: disable=super-init-not-called
    def __init__(self, msg, parser_token=None):
        """
        Parameters:

          msg (:term:`string`):
            Message text describing the error.

          parser_token (`lex.LexToken` or `yacc.YaccProduction`):
            PLY lex or yacc parser token (that is, the ``p`` argument of a yacc
            parser function or the ``t`` argument of a lex parser function).
            This token is used to obtain the MOF source text and location
            information.

            `None` will result in no MOF source text and location information
            to be obtained.
        """
        assert msg is not None
        self._msg = msg
        if parser_token is None:
            self.args = (None, None, None, None)
        else:
            assert isinstance(
                parser_token,
                (lex.LexToken, yacc.YaccProduction))
            mof_ = parser_token.lexer.parser.mof
            self.args = (parser_token.lexer.lineno,
                         _find_column(mof_, parser_token),
                         parser_token.lexer.parser.file,
                         _get_error_context(mof_, parser_token))

    @property
    def lineno(self):
        """
        :term:`integer`: Line number in the MOF file or MOF string where the
        error occurred (1-based).
        """
        return self.args[0]

    @property
    def column(self):
        """
        :term:`integer`: Position within the line in the MOF file or MOF string
        where the error occurred (1-based).
        """
        return self.args[1]

    @property
    def file(self):
        """
        :term:`string`: File name of the MOF file where the error occurred.

        `None` if the error occurred in a MOF string that was compiled.
        """
        return self.args[2]

    @property
    def context(self):
        """
        :term:`string`: MOF context, consisting of a first line that is the
        MOF line in error, and a second line that uses the '^' character to
        indicate the position of the token in error in the MOF line.
        """
        return self.args[3]

    @property
    def msg(self):
        """
        :term:`string`: Message text describing the error.
        """
        return self._msg

    def __str__(self):
        return self.get_err_msg()

    def get_err_msg(self):
        """
        Return a multi-line error message for being printed, in the following
        format. The text in angle brackets refers to the same-named properties
        of the exception instance:

        ::

            <error kind>:<file>:<lineno>:<colno>: <msg>
            <context - MOF line>
            <context - position indicator line>

        Returns:

          :term:`string`: Multi-line error message.
        """
        ret_str = f'{self.error_kind}:'
        disp_file = 'String' if not self.file else self.file
        if self.lineno is not None:
            ret_str += _format("{0}:{1}:{2}",
                               disp_file, self.lineno, self.column)
        if self.msg:
            ret_str += _format(" {0}", self.msg)
        if self.context is not None:
            ret_str += '\n'
            ret_str += '\n'.join(self.context)
        return ret_str


class MOFParseError(MOFCompileError):
    """
    Exception indicating that MOF cannot be parsed correctly, e.g. for
    syntax errors.

    Derived from :exc:`~pywbem.MOFCompileError`.
    """

    error_kind = "MOF parsing error"


class MOFDependencyError(MOFCompileError):
    """
    Exception indicating that MOF cannot be compiled because of a missing
    dependency. For example, the MOF to be compiled specifies a class but the
    superclass of the class cannot be found.

    Derived from :exc:`~pywbem.MOFCompileError`.
    """

    error_kind = "MOF dependency error"


class MOFRepositoryError(MOFCompileError):
    """
    Exception indicating that MOF cannot be compiled because of a CIM error
    returned by the target CIM repository. The CIM error is attached to this
    exception and is part of the exception message.

    Derived from :exc:`~pywbem.MOFCompileError`.
    """

    error_kind = "CIM repository error"

    def __init__(self, msg, parser_token=None, cim_error=None):
        """
        Parameters:

          msg (:term:`string`):
            Message text describing the error.

          parser_token (`lex.LexToken` or `yacc.YaccProduction`):
            PLY lex or yacc parser token (that is, the ``p`` argument of a yacc
            parser function or the ``t`` argument of a lex parser function).
            This token is used to obtain the MOF source text and location
            information.

            `None` will result in no MOF source text and location information
            to be obtained.

          cim_error (:class:`~pywbem.CIMError`):
            CIM error returned by the CIM repository.
        """
        super().__init__(msg, parser_token)
        self._cim_error = cim_error

    @property
    def cim_error(self):
        """
        :class:`~pywbem.CIMError`: CIM error returned by the CIM repository.
        """
        return self._cim_error

    def get_err_msg(self):
        """
        Return a multi-line error message for being printed, in the following
        format. The text in angle brackets refers to the same-named properties
        of the exception instance:

        ::

            <error kind>:<file>:<lineno>:<colno>: <msg>
            <context - MOF line>
            <context - position indicator line>
            <CIM error>

        Returns:

          :term:`string`: Multi-line error message.
        """
        ret_str = super().get_err_msg()
        ret_str += f"\n{self.cim_error}"
        return ret_str


class MOFCompilerSetupError(Exception):
    """
    Exception indicating that the MOF compiler cannot be set up.

    Derived from :exc:`Exception`.
    """
    pass


def p_error(p):
    """
        YACC Error Callback from the parser.  The parameter is the token
        in error and contains information on the file and position of the
        error. If p is `None`, PLY is returning eof error.
    """

    if p is None:
        raise MOFParseError(msg='Unexpected end of MOF')

    msg = p.lexer.last_msg
    p.lexer.last_msg = None
    if not msg:
        msg = "MOF grammar error"
    raise MOFParseError(msg=msg, parser_token=p)


# pylint: disable=unused-argument
def p_mofSpecification(p):
    """mofSpecification : mofProductionList"""


# pylint: disable=unused-argument
def p_mofProductionList(p):
    """mofProductionList : empty
                         | mofProductionList mofProduction
                         """


# pylint: disable=unused-argument
def p_mofProduction(p):
    """mofProduction : compilerDirective
                     | mp_createClass
                     | mp_setQualifier
                     | mp_createInstance
                     """


def p_mp_createClass(p):
    """mp_createClass : classDeclaration
                      """

    # pylint: disable=too-many-branches,too-many-statements,too-many-locals

    ns = p.parser.target_namespace or p.parser.handle.default_namespace
    cc = p[1]
    cc_path = CIMClassName(namespace=ns, classname=cc.classname)

    # Compile class invalid when in mode to compile embedded instance
    if p.parser.embedded_objects is not None:
        raise MOFParseError(
            msg=_format(
                "Invalid compile of CIMClass {0}. "
                "Compiler in mode to compile embedded instance and"
                "compile of other types is invalid", cc))
    try:
        fixedNS = fixedRefs = fixedSuper = False
        while not fixedNS or not fixedRefs or not fixedSuper:
            try:
                if p.parser.verbose:
                    p.parser.log(
                        _format("Creating class {0}", cc_path))
                p.parser.handle.CreateClass(cc, namespace=ns)
                try:
                    p.parser.classnames[ns].append(cc.classname.lower())
                except KeyError:
                    p.parser.classnames[ns] = [cc.classname.lower()]
                break
            except CIMError as ce:
                errcode = ce.status_code

                if errcode == CIM_ERR_INVALID_NAMESPACE:
                    assert not fixedNS  # Should not happen if we created it
                    if p.parser.verbose:
                        p.parser.log(
                            _format("Creating namespace {0} (in MOF compiler)",
                                    ns))
                    p.parser.server.create_namespace(ns)
                    fixedNS = True
                    continue  # Try again to create the class

                if errcode == CIM_ERR_INVALID_SUPERCLASS:
                    assert not fixedSuper  # Should not happen if we fixed it
                    moffile = p.parser.mofcomp.find_mof(cc.superclass)
                    if not moffile:
                        raise MOFDependencyError(
                            msg=_format(
                                "Cannot compile class {0} because its "
                                "superclass {1!A} does not exist in the CIM "
                                "repository and a MOF file for it was not "
                                "found on the search path",
                                cc_path, cc.superclass),
                            parser_token=p)
                    p.parser.mofcomp.compile_file(moffile, ns)
                    fixedSuper = True
                    continue  # Try again to create the class

                if errcode in [CIM_ERR_INVALID_PARAMETER,
                               CIM_ERR_NOT_FOUND,
                               CIM_ERR_FAILED]:
                    # Should not happend if we fixed the issues
                    if fixedRefs:
                        raise MOFDependencyError(
                            msg=_format(
                                "Cannot compile class {0} because "
                                "errorcode={1} ({2!A}) was returned from "
                                "CreateClass. The CreateClass exception was "
                                "{3!A}",
                                cc_path, errcode, ce.status_code_name,
                                ce),
                            parser_token=p)

                    if not p.parser.qualcache[ns]:
                        for fname in ['qualifiers', 'qualifiers_optional']:
                            qualfile = p.parser.mofcomp.find_mof(fname)
                            if qualfile:
                                p.parser.mofcomp.compile_file(qualfile, ns)
                    if not p.parser.qualcache[ns]:
                        raise MOFDependencyError(
                            msg=_format(
                                "Cannot compile class {0} because the CIM "
                                "repository does not contain any qualifiers "
                                "and the qualifier files 'qualifiers.mof' and "
                                "'qualifiers_optional.mof' were not found on "
                                "the search path or did not specify any "
                                "qualifiers",
                                cc_path),
                            parser_token=p)
                    objects = list(cc.properties.values())
                    for meth in cc.methods.values():
                        objects += list(meth.parameters.values())

                    dep_classnames = NocaseList()
                    ccname = cc.classname.lower()
                    for obj in objects:
                        if obj.type == 'reference':
                            if obj.reference_class not in dep_classnames and \
                                    obj.reference_class.lower() != ccname:
                                dep_classnames.append(obj.reference_class)
                        elif obj.type == 'string':
                            try:
                                embedded_inst = \
                                    obj.qualifiers['embeddedinstance']
                            except KeyError:
                                continue
                            if embedded_inst.value not in dep_classnames and \
                                    embedded_inst.value.lower() != ccname:
                                dep_classnames.append(embedded_inst.value)
                    for cln in dep_classnames:
                        if cln in p.parser.classnames[ns]:
                            continue
                        try:
                            # Don't limit it with LocalOnly=True,
                            # PropertyList, IncludeQualifiers=False, ...
                            # because of caching in case we're using the
                            # special WBEMConnection subclass used for
                            # removing schema elements
                            p.parser.handle.GetClass(cln,
                                                     namespace=ns,
                                                     LocalOnly=False,
                                                     IncludeQualifiers=True)
                        except CIMError:
                            moffile = p.parser.mofcomp.find_mof(cln)
                            if not moffile:
                                raise MOFDependencyError(
                                    msg=_format(
                                        "Cannot compile class {0} because "
                                        "its dependent class {1!A} does not "
                                        "exist in the CIM repository and a "
                                        "MOF file for it was not found on the "
                                        "search path",
                                        cc_path, cln),
                                    parser_token=p)
                            if p.parser.verbose:
                                p.parser.log(
                                    _format("Class {0} depends on class {1!A} "
                                            "which is not in repository.",
                                            cc_path, cln))
                            p.parser.mofcomp.compile_file(moffile, ns)

                        p.parser.classnames[ns].append(cln)
                    fixedRefs = True
                    continue  # Try again to create the class

                # The options for fixing dependency issues have been exhausted.
                # Re-raise the CIMError from CreateClass.
                raise

    except CIMError as ce:

        if ce.status_code != CIM_ERR_ALREADY_EXISTS:
            raise MOFRepositoryError(
                msg=_format(
                    "Cannot compile class {0} because the CIM repository "
                    "returned an error for CreateClass",
                    cc_path),
                parser_token=p,
                cim_error=ce)

        if p.parser.verbose:
            p.parser.log(
                _format("Class already exists - modifying class {0}",
                        cc_path))

        # Attempt to modify class since it exists.
        try:
            p.parser.handle.ModifyClass(cc, ns)

        # Handle exceptions from ModifyClass.
        except CIMError as ce2:
            if p.parser.verbose:
                p.parser.log(
                    _format("Error modifying class {0}: {1}, {2}",
                            cc_path, ce2.status_code, ce2.status_description))
            raise MOFRepositoryError(
                msg=_format(
                    "Cannot compile class {0} because the class already "
                    "exists and the CIM repository returned an error for "
                    "ModifyClass",
                    cc_path),
                parser_token=p,
                cim_error=ce2)


def p_mp_createInstance(p):
    """mp_createInstance : instanceDeclaration"""

    # p[1] is a list of instance and any alias defined in instanceDeclaration
    input_ = p[1]
    inst = input_[0]
    alias = input_[1]  # alias may be valid alias or None
    ns = p.parser.target_namespace or p.parser.handle.default_namespace
    classpath = CIMClassName(namespace=ns, classname=inst.classname)

    if p.parser.verbose:
        p.parser.log(
            _format("Creating instance of class {0}", classpath))

    # If embedded_instances flag set, save instance to this
    # variable to be set into instance value rather than inserting
    # into repository.
    if p.parser.embedded_objects is not None:
        p.parser.embedded_objects.append(inst)
        return

    try:
        instpath = p.parser.handle.CreateInstance(inst, namespace=ns)
    except CIMError as ce:
        if ce.status_code == CIM_ERR_ALREADY_EXISTS:

            # If CreateInstance fails with CIM_ERR_ALREADY_EXISTS, the client
            # does not get back the instance path of the already existing
            # instance.
            # We therefore create an instance path from the key properties
            # specified in the input instance.
            # The basic issue with this approach is that an instance provider
            # in the WBEM server could have determined key properties different
            # from or in addition to the ones specified in the input instance.
            # A typical example is InstanceID that is not specified in the
            # input instance but is determined by the provider.
            # This issue results in a limitation of this approach.
            if p.parser.verbose:
                p.parser.log(
                    _format("Instance already exists - retrieving its class "
                            "{0}:{1}", ns, inst.classname))
            try:
                cls = p.parser.handle.GetClass(
                    inst.classname, namespace=ns, LocalOnly=False)
            except CIMError as ce2:
                raise MOFRepositoryError(
                    msg=_format(
                        "Cannot compile instance of {0!A} because the CIM "
                        "repository returned an error for GetClass",
                        inst.classname),
                    parser_token=p,
                    cim_error=ce2)
            try:
                instpath = CIMInstanceName.from_instance(
                    cls, inst, namespace=ns, strict=True)
            except ValueError as ve:
                # key properties do not exist in the instance
                raise MOFRepositoryError(
                    msg=_format(
                        "Cannot compile instance of {0!A} because its instance "
                        "path cannot be created from the instance: {}",
                        inst.classname, ve),
                    parser_token=p)

            if p.parser.verbose:
                p.parser.log(
                    _format("Modifying instance {0}", instpath))

            inst.path = instpath
            try:
                p.parser.handle.ModifyInstance(inst)
            except CIMError as ce2:
                # modify failed, output original error
                raise MOFRepositoryError(
                    msg=_format(
                        "Cannot compile instance of {0!A} because the CIM "
                        "repository returned an error for ModifyInstance",
                        inst.classname),
                    parser_token=p,
                    cim_error=ce2)
        else:
            raise MOFRepositoryError(
                msg=_format(
                    "Cannot compile instance of {0!A} because the CIM "
                    "repository returned an error for CreateInstance",
                    inst.classname),
                parser_token=p,
                cim_error=ce)

    # Set the returned or constructed instance path into the alias table
    if alias:
        p.parser.aliases[alias] = instpath


def p_mp_setQualifier(p):
    """mp_setQualifier : qualifierDeclaration"""
    qualdecl = p[1]
    if p.parser.embedded_objects is not None:
        raise MOFParseError(
            msg=_format(
                "Invalid compile of CIMQualifierDeclaration {0}. "
                "Compiler in mode to compile Embedded instance and"
                "compile of other types is invalid", qualdecl))
    ns = p.parser.target_namespace or p.parser.handle.default_namespace
    if p.parser.verbose:
        p.parser.log(
            _format("Setting qualifier {0}:{1}",
                    ns, qualdecl.name))
    try:
        p.parser.handle.SetQualifier(qualdecl, namespace=ns)
    except CIMError as ce:
        if ce.status_code == CIM_ERR_INVALID_NAMESPACE:
            if p.parser.verbose:
                p.parser.log(
                    _format("Creating namespace {0} (in MOF compiler)", ns))
            p.parser.server.create_namespace(ns)
            if p.parser.verbose:
                p.parser.log(
                    _format("Setting qualifier {0}:{1}", ns, qualdecl.name))
            p.parser.handle.SetQualifier(qualdecl, namespace=ns)
        elif ce.status_code == CIM_ERR_NOT_SUPPORTED:
            if p.parser.verbose:
                p.parser.log(
                    _format("Qualifier {0}:{1} already exists. Deleting...",
                            ns, qualdecl.name))
            p.parser.handle.DeleteQualifier(qualdecl.name)
            if p.parser.verbose:
                p.parser.log(
                    _format("Setting qualifier {0}:{1}", ns, qualdecl.name))
            p.parser.handle.SetQualifier(qualdecl, namespace=ns)
        else:
            raise MOFRepositoryError(
                msg=_format(
                    "Cannot compile qualifier declaration {0!A} because the "
                    "CIM repository returned an error for SetQualifier",
                    qualdecl.name),
                parser_token=p,
                cim_error=ce)
    p.parser.qualcache[ns][qualdecl.name] = qualdecl


def p_compilerDirective(p):
    """compilerDirective : '#' PRAGMA pragmaName '(' pragmaParameter ')'"""
    directive = p[3].lower()
    param = p[5]

    if directive == 'include':
        fname = param
        if p.parser.file:
            if os.path.dirname(p.parser.file):
                fname = os.path.join(os.path.dirname(p.parser.file),
                                     fname)
        p.parser.mofcomp.compile_file(fname, p.parser.target_namespace)

    elif directive == 'namespace':
        # parse the param to separate out namespace from other wbemuri pieces
        m = WBEM_URI_NAMESPACEPATH_REGEXP.match(param)
        ns_type = m.group(1) or None
        host = m.group(2) or None
        namespace = m.group(3) or None
        if m is None or ns_type or host or namespace is None:
            raise MOFParseError(
                msg=_format(
                    "Invalid pragma namespace path: {0!A}. Only namespace name "
                    "component allowed", param),
                parser_token=p)

        if p.parser.verbose:
            p.parser.log(
                _format("Switching target namespace to {0!A}", namespace))
        p.parser.target_namespace = namespace

        if namespace not in p.parser.qualcache:
            p.parser.qualcache[namespace] = NocaseDict()

    p[0] = None


def p_pragmaName(p):
    """pragmaName : identifier"""
    p[0] = p[1]


def p_pragmaParameter(p):
    """pragmaParameter : stringValue"""
    p[0] = _fixStringValue(p[1], p)


def p_classDeclaration(p):
    # pylint: disable=line-too-long
    """classDeclaration : CLASS className '{' classFeatureList '}' ';'
                        | CLASS className superClass '{' classFeatureList '}' ';'
                        | CLASS className alias '{' classFeatureList '}' ';'
                        | CLASS className alias superClass '{' classFeatureList '}' ';'
                        | qualifierList CLASS className '{' classFeatureList '}' ';'
                        | qualifierList CLASS className superClass '{' classFeatureList '}' ';'
                        | qualifierList CLASS className alias '{' classFeatureList '}' ';'
                        | qualifierList CLASS className alias superClass '{' classFeatureList '}' ';'
                        """  # noqa: E501
    superclass = None
    alias = None
    quals = []
    if isinstance(p[1], str):  # no class qualifiers
        cname = p[2]
        if p[3][0] == '$':  # alias present
            alias = p[3]
            if p[4] == '{':  # no superclass
                cfl = p[5]
            else:  # superclass
                superclass = p[4]
                cfl = p[6]
        else:  # no alias
            if p[3] == '{':  # no superclass
                cfl = p[4]
            else:  # superclass
                superclass = p[3]
                cfl = p[5]
    else:  # class qualifiers
        quals = p[1]
        cname = p[3]
        if p[4][0] == '$':  # alias present
            alias = p[4]
            if p[5] == '{':  # no superclass
                cfl = p[6]
            else:  # superclass
                superclass = p[5]
                cfl = p[7]
        else:  # no alias
            if p[4] == '{':  # no superclass
                cfl = p[5]
            else:  # superclass
                superclass = p[4]
                cfl = p[6]
    quals = OrderedDict([(x.name, x) for x in quals])
    methods = OrderedDict()
    props = OrderedDict()
    for item in cfl:
        item.class_origin = cname
        if isinstance(item, CIMMethod):
            methods[item.name] = item
        else:
            props[item.name] = item
    p[0] = CIMClass(cname, properties=props, methods=methods,
                    superclass=superclass, qualifiers=quals)
    if alias:
        p.parser.aliases[alias] = p[0]


def p_classFeatureList(p):
    """classFeatureList : empty
                        | classFeatureList classFeature
                        """
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]


def p_qualifierListEmpty(p):
    """qualifierListEmpty : empty
                          | qualifierListEmpty ',' qualifier
                          """
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[3]]


def p_className(p):
    """className : identifier"""
    p[0] = p[1]


def p_alias(p):
    """alias : AS aliasIdentifier"""
    p[0] = p[2]


def p_aliasIdentifier(p):
    """aliasIdentifier : '$' identifier"""
    p[0] = f'${p[2]}'


def p_superClass(p):
    """superClass : ':' className"""
    p[0] = p[2]


def p_classFeature(p):
    """classFeature : propertyDeclaration
                    | methodDeclaration
                    | referenceDeclaration
                    """
    p[0] = p[1]


def p_qualifierList(p):
    """qualifierList : '[' qualifier qualifierListEmpty ']'"""
    p[0] = [p[2]] + p[3]


def p_qualifier(p):
    """qualifier : qualifierName
                 | qualifierName ':' flavorList
                 | qualifierName qualifierParameter
                 | qualifierName qualifierParameter ':' flavorList
                 """

    # pylint: disable=too-many-branches
    qname = p[1]
    ns = p.parser.target_namespace or p.parser.handle.default_namespace
    qval = None
    flavorlist = []
    if len(p) == 3:
        qval = p[2]
    elif len(p) == 4:
        flavorlist = p[3]
    elif len(p) == 5:
        qval = p[2]
        flavorlist = p[4]
    try:
        qualdecl = p.parser.qualcache[ns][qname]
    except KeyError:
        try:
            quals = p.parser.handle.EnumerateQualifiers(namespace=ns)
        except CIMError as ce:
            if ce.status_code != CIM_ERR_INVALID_NAMESPACE:
                raise MOFRepositoryError(
                    msg=_format(
                        "Cannot compile element specifying qualifier {0!A} "
                        "because the CIM repository returned an error for "
                        "EnumerateQualifiers",
                        qname),
                    parser_token=p,
                    cim_error=ce)
            if p.parser.verbose:
                p.parser.log(
                    _format("Creating namespace {0} (in MOF compiler)", ns))
            p.parser.server.create_namespace(ns)
            quals = None

        if quals:
            for qual in quals:
                p.parser.qualcache[ns][qual.name] = qual
        else:
            for fname in ['qualifiers', 'qualifiers_optional']:
                qualfile = p.parser.mofcomp.find_mof(fname)
                if qualfile:
                    p.parser.mofcomp.compile_file(qualfile, ns)
    try:
        qualdecl = p.parser.qualcache[ns][qname]
    except KeyError:
        raise MOFDependencyError(
            msg=_format(
                "Cannot compile element specifying qualifier {0!A} because "
                "its qualifier declaration does not exist in the "
                "CIM repository and was not found in the qualifier files "
                "'qualifiers.mof' and  'qualifiers_optional.mof' on the "
                "search path",
                qname),
            parser_token=p)

    flavors = _build_flavors(p, flavorlist, qualdecl, qualdecl.name)
    if qval is None:
        if qualdecl.type == 'boolean':
            qval = True
        else:
            qval = qualdecl.value  # default value
    else:
        qval = cimvalue(qval, qualdecl.type)
    p[0] = CIMQualifier(qname, qval, type=qualdecl.type, **flavors)

    # Note: The propagated flag is not set because this is parsed MOF, which
    # contains specified qualifiers and not propagated qualifiers.


def p_flavorList(p):
    """flavorList : flavor
                  | flavorList flavor
                  """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]


def p_qualifierParameter(p):
    """qualifierParameter : '(' constantValue ')'
                          | arrayInitializer
                          """
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]


# Note: TOINSTANCE is deprecated in DSP0201 and is not specified in DSP004.
# Pywbem supports TOINSTANCE as deprecated, for historical reasons.
def p_flavor(p):
    """flavor : ENABLEOVERRIDE
              | DISABLEOVERRIDE
              | RESTRICTED
              | TOSUBCLASS
              | TOINSTANCE
              | TRANSLATABLE
              """
    p[0] = p[1].lower()


def p_propertyDeclaration(p):
    """propertyDeclaration : propertyDeclaration_1
                           | propertyDeclaration_2
                           | propertyDeclaration_3
                           | propertyDeclaration_4
                           | propertyDeclaration_5
                           | propertyDeclaration_6
                           | propertyDeclaration_7
                           | propertyDeclaration_8
                           """
    p[0] = p[1]


def p_propertyDeclaration_1(p):
    """propertyDeclaration_1 : dataType propertyName ';'"""
    p[0] = CIMProperty(p[2], None, type=p[1])


def p_propertyDeclaration_2(p):
    """propertyDeclaration_2 : dataType propertyName defaultValue ';'"""
    p[0] = CIMProperty(p[2], p[3], type=p[1])


def p_propertyDeclaration_3(p):
    """propertyDeclaration_3 : dataType propertyName array ';'"""
    p[0] = CIMProperty(p[2], None, type=p[1], is_array=True,
                       array_size=p[3])


def p_propertyDeclaration_4(p):
    """propertyDeclaration_4 : dataType propertyName array defaultValue ';'"""
    p[0] = CIMProperty(p[2], p[4], type=p[1], is_array=True,
                       array_size=p[3])


def p_propertyDeclaration_5(p):
    """propertyDeclaration_5 : qualifierList dataType propertyName ';'"""
    quals = OrderedDict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], None, type=p[2], qualifiers=quals)


def p_propertyDeclaration_6(p):
    # pylint: disable=line-too-long
    """propertyDeclaration_6 : qualifierList dataType propertyName defaultValue ';'"""  # noqa: E501
    quals = OrderedDict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], cimvalue(p[4], p[2]),
                       type=p[2], qualifiers=quals)


def p_propertyDeclaration_7(p):
    """propertyDeclaration_7 : qualifierList dataType propertyName array ';'"""
    quals = OrderedDict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], None, type=p[2], qualifiers=quals,
                       is_array=True, array_size=p[4])


def p_propertyDeclaration_8(p):
    # pylint: disable=line-too-long
    """propertyDeclaration_8 : qualifierList dataType propertyName array defaultValue ';'"""  # noqa: E501
    quals = OrderedDict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], cimvalue(p[5], p[2]),
                       type=p[2], qualifiers=quals, is_array=True,
                       array_size=p[4])


def p_referenceDeclaration(p):
    # pylint: disable=line-too-long
    """referenceDeclaration : objectRef referenceName ';'
                            | objectRef referenceName defaultValue ';'
                            | qualifierList objectRef referenceName ';'
                            | qualifierList objectRef referenceName defaultValue ';'
                            """  # noqa: E501
    quals = []
    dv = None
    if isinstance(p[1], list):  # qualifiers
        quals = p[1]
        cname = p[2]
        pname = p[3]
        if len(p) == 6:
            dv = p[4]
    else:
        cname = p[1]
        pname = p[2]
        if len(p) == 5:
            dv = p[3]
    quals = OrderedDict([(x.name, x) for x in quals])
    p[0] = CIMProperty(pname, dv, type='reference',
                       reference_class=cname, qualifiers=quals)


def p_methodDeclaration(p):
    # pylint: disable=line-too-long
    """methodDeclaration : dataType methodName '(' ')' ';'
                         | dataType methodName '(' parameterList ')' ';'
                         | qualifierList dataType methodName '(' ')' ';'
                         | qualifierList dataType methodName '(' parameterList ')' ';'
                         """  # noqa: E501
    paramlist = []
    quals = []
    if isinstance(p[1], str):  # no quals
        dt = p[1]
        mname = p[2]
        if p[4] != ')':
            paramlist = p[4]
    else:  # quals present
        quals = p[1]
        dt = p[2]
        mname = p[3]
        if p[5] != ')':
            paramlist = p[5]
    params = OrderedDict([(param.name, param) for param in paramlist])
    quals = OrderedDict([(q.name, q) for q in quals])
    p[0] = CIMMethod(mname, return_type=dt, parameters=params,
                     qualifiers=quals)

    # Note: class_origin is set when adding method to class.

    # Note: The propagated flag is not set because this is parsed MOF, which
    # contains specified methods and not any inherited methods.


def p_propertyName(p):
    """propertyName : identifier"""
    p[0] = p[1]


def p_referenceName(p):
    """referenceName : identifier"""
    p[0] = p[1]


def p_methodName(p):
    """methodName : identifier"""
    p[0] = p[1]


def p_dataType(p):
    """dataType : DT_UINT8
                | DT_SINT8
                | DT_UINT16
                | DT_SINT16
                | DT_UINT32
                | DT_SINT32
                | DT_UINT64
                | DT_SINT64
                | DT_REAL32
                | DT_REAL64
                | DT_CHAR16
                | DT_STR
                | DT_BOOL
                | DT_DATETIME
                """
    p[0] = p[1].lower()


def p_objectRef(p):
    """objectRef : className REF"""
    p[0] = p[1]


def p_parameterList(p):
    """parameterList : parameter
                     | parameterList ',' parameter
                     """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_parameter(p):
    """parameter : parameter_1
                 | parameter_2
                 | parameter_3
                 | parameter_4
                 """
    p[0] = p[1]


def p_parameter_1(p):
    """parameter_1 : dataType parameterName
                   | dataType parameterName array
                   """
    args = {}
    if len(p) == 4:
        args['is_array'] = True
        args['array_size'] = p[3]
    p[0] = CIMParameter(p[2], p[1], **args)


def p_parameter_2(p):
    """parameter_2 : qualifierList dataType parameterName
                   | qualifierList dataType parameterName array
                   """
    args = {}
    if len(p) == 5:
        args['is_array'] = True
        args['array_size'] = p[4]
    quals = OrderedDict([(x.name, x) for x in p[1]])
    p[0] = CIMParameter(p[3], p[2], qualifiers=quals, **args)


def p_parameter_3(p):
    """parameter_3 : objectRef parameterName
                   | objectRef parameterName array
                   """
    args = {}
    if len(p) == 4:
        args['is_array'] = True
        args['array_size'] = p[3]
    p[0] = CIMParameter(p[2], 'reference', reference_class=p[1], **args)


def p_parameter_4(p):
    """parameter_4 : qualifierList objectRef parameterName
                   | qualifierList objectRef parameterName array
                   """
    args = {}
    if len(p) == 5:
        args['is_array'] = True
        args['array_size'] = p[4]
    quals = OrderedDict([(x.name, x) for x in p[1]])
    p[0] = CIMParameter(p[3], 'reference', qualifiers=quals,
                        reference_class=p[2], **args)


def p_parameterName(p):
    """parameterName : identifier"""
    p[0] = p[1]


def p_array(p):
    """array : '[' ']'
             | '[' integerValue ']'
             """
    if len(p) == 3:
        p[0] = None
    else:
        p[0] = p[2]


def p_defaultValue(p):
    """defaultValue : '=' initializer"""
    p[0] = p[2]


def p_initializer(p):
    """initializer : constantValue
                   | arrayInitializer
                   | referenceInitializer
                   """
    p[0] = p[1]


def p_arrayInitializer(p):
    """arrayInitializer : '{' constantValueList '}'
                        | '{' '}'
                        """
    if len(p) == 3:
        p[0] = []
    else:
        p[0] = p[2]


def p_constantValueList(p):
    """constantValueList : constantValue
                         | constantValueList ',' constantValue
                         """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def _fixStringValue(s, p):
    """Clean up string value including special characters, etc."""

    # pylint: disable=too-many-branches
    s = s[1:-1]
    rv = ''
    esc = False
    i = -1
    while i < len(s) - 1:
        i += 1
        ch = s[i]
        if ch == '\\' and not esc:
            esc = True
            continue
        if not esc:
            rv += ch
            continue

        if ch == '"':
            rv += '"'
        elif ch == 'n':
            rv += '\n'
        elif ch == 't':
            rv += '\t'
        elif ch == 'b':
            rv += '\b'
        elif ch == 'f':
            rv += '\f'
        elif ch == 'r':
            rv += '\r'
        elif ch == '\\':
            rv += '\\'
        elif ch in ['x', 'X']:
            hexc = 0
            j = 0
            i += 1
            while j < 4:
                c = s[i + j]
                c = c.upper()
                if not c.isdigit() and c not in 'ABCDEF':
                    break
                hexc <<= 4
                if c.isdigit():
                    hexc |= ord(c) - ord('0')
                else:
                    hexc |= ord(c) - ord('A') + 0XA
                j += 1
            if j == 0:
                # DSP0004 requires 1..4 hex chars - we have 0
                raise MOFParseError(
                    msg="Unicode escape sequence (e.g. '\\x12AB') requires "
                        "at least one hex character",
                    parser_token=p)
            rv += chr(hexc)
            i += j - 1

        esc = False

    return rv


def p_stringValueList(p):
    """stringValueList : stringValue
                       | stringValueList stringValue
                       """
    if len(p) == 2:
        p[0] = _fixStringValue(p[1], p)
    else:
        p[0] = p[1] + _fixStringValue(p[2], p)


def p_constantValue(p):
    """constantValue : integerValue
                     | floatValue
                     | charValue
                     | stringValueList
                     | booleanValue
                     | nullValue
                     """
    # The lexer functions (t_floatValue(), etc.) return a properly typed value.
    p[0] = p[1]


def p_integerValue(p):
    """integerValue : binaryValue
                    | octalValue
                    | decimalValue
                    | hexValue
                    """
    # The lexer functions (t_binaryValue(), etc.) return a properly typed value.
    p[0] = p[1]


def p_referenceInitializer(p):
    """referenceInitializer : objectHandle
                            | aliasIdentifier
                            """
    if p[1][0] == '$':
        try:
            p[0] = p.parser.aliases[p[1]]
        except KeyError:
            raise MOFParseError(
                msg=_format(
                    "Cannot compile reference initialization because the "
                    "instance alias {0!A} was not previously defined in "
                    "in the MOF", p[1]),
                parser_token=p)
    else:
        p[0] = p[1]


def p_objectHandle(p):
    """objectHandle : identifier"""
    p[0] = p[1]


def p_qualifierDeclaration(p):
    # pylint: disable=line-too-long
    """qualifierDeclaration : QUALIFIER qualifierName qualifierType scope ';'
                            | QUALIFIER qualifierName qualifierType scope defaultFlavor ';'
                            """  # noqa: E501
    qualtype = p[3]
    dt, is_array, array_size, value = qualtype
    qualname = p[2]
    scopes = p[4]
    if len(p) == 5:
        flist = []
    else:
        flist = p[5]

    flavors = _build_flavors(p, flist, None, qualname)

    p[0] = CIMQualifierDeclaration(
        qualname, dt, value=value, is_array=is_array, array_size=array_size,
        scopes=scopes, **flavors)


def _build_flavors(p, flist, qualdecl, qualname):
    """
        Build and return a dictionary defining the flavors from the
        flist argument.

        This function maps from the input keyword definitions for the flavors
        (ex. EnableOverride) to the PyWBEM internal definitions
        (ex. overridable)

        Uses the qualdecl argument as a basis if it exists. This is to define
        qualifier flavors if qualfier declaractions exist.

        This applies the values from the qualifierDecl to the the qualifier
        flavor list.

        This function and the defaultflavor function insure that all
        flavors are defined in the created dictionary that is returned. This
        is important because the PyWBEM classes allow `None` as a flavor
        definition.
    """

    flavors = {}
    if ('disableoverride' in flist and 'enableoverride' in flist) or \
            ('restricted' in flist and 'tosubclass' in flist):  # noqa: E125
        raise MOFParseError(
            msg=_format(
                "Cannot compile qualifier declaration {0!A} because it "
                "specifies conflicting flavors: {1}",
                qualname, flist),
            parser_token=p)

    if qualdecl is not None:
        flavors = {'overridable': qualdecl.overridable,
                   'translatable': qualdecl.translatable,
                   'tosubclass': qualdecl.tosubclass,
                   'toinstance': qualdecl.toinstance}
    if 'disableoverride' in flist:
        flavors['overridable'] = False
    if 'enableoverride' in flist:
        flavors['overridable'] = True
    if 'translatable' in flist:
        flavors['translatable'] = True
    if 'restricted' in flist:
        flavors['tosubclass'] = False
    if 'tosubclass' in flist:
        flavors['tosubclass'] = True
    if 'toinstance' in flist:
        flavors['toinstance'] = True
    # issue #193 ks 5/16 removed tosubclass & set toinstance.

    return flavors

# The ASSOCIATION and INDICATION alternates are required because ASSOCIATION
# and INDICATION are reserved words as defined in the DMTF spec but also
# keywords in this LEX definition and used as part of the scope definition


def p_qualifierName(p):
    """qualifierName : identifier
                     | ASSOCIATION
                     | INDICATION
                     """
    p[0] = p[1]


def p_qualifierType(p):
    """qualifierType : qualifierType_1
                     | qualifierType_2
                     """
    p[0] = p[1]


def p_qualifierType_1(p):
    """qualifierType_1 : ':' dataType array
                       | ':' dataType array defaultValue
                       """
    dv = None
    if len(p) == 5:
        dv = p[4]
    p[0] = (p[2], True, p[3], dv)


def p_qualifierType_2(p):
    """qualifierType_2 : ':' dataType
                       | ':' dataType defaultValue
                       """
    dv = None
    if len(p) == 4:
        dv = p[3]
    p[0] = (p[2], False, None, dv)


def p_scope(p):
    """scope : ',' SCOPE '(' scopeElementList ')'"""
    slist = p[4]
    # Create dictionary of all scope keywords where value is True if
    # the keyword is in slist, otherwise False.
    scopes = OrderedDict()
    for i in ('CLASS',
              'ASSOCIATION',
              'INDICATION',
              'PROPERTY',
              'REFERENCE',
              'METHOD',
              'PARAMETER',
              'ANY'):
        scopes[i] = i in slist
    p[0] = scopes


def p_scopeElementList(p):
    """scopeElementList : scopeElement
                       | scopeElementList ',' scopeElement
                       """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_scopeElement(p):
    """scopeElement : CLASS
                   | ASSOCIATION
                   | INDICATION
                   | PROPERTY
                   | REFERENCE
                   | METHOD
                   | PARAMETER
                   | ANY
                   """
    p[0] = p[1].upper()


def p_defaultFlavor(p):
    """defaultFlavor : ',' FLAVOR '(' flavorListWithComma ')'"""
    flist = p[4]
    # Create dictionary of default flavors based on DSP0004 definition
    # of defaults for flavors. This insures that all possible flavors keywords
    # are defined in the created dictionary.
    flavors = {'ENABLEOVERRIDE': True,
               'TOSUBCLASS': True,
               'TOINSTANCE': False,
               'DISABLEOVERRIDE': False,
               'RESTRICTED': False,
               'TRANSLATABLE': False}
    for i in flist:
        flavors[i] = True
    p[0] = flavors


def p_flavorListWithComma(p):
    """flavorListWithComma : flavor
                           | flavorListWithComma ',' flavor
                           """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_instanceDeclaration(p):
    # pylint: disable=line-too-long
    """instanceDeclaration : INSTANCE OF className '{' valueInitializerList '}' ';'
                           | INSTANCE OF className alias '{' valueInitializerList '}' ';'
                           | qualifierList INSTANCE OF className '{' valueInitializerList '}' ';'
                           | qualifierList INSTANCE OF className alias '{' valueInitializerList '}' ';'
                           """  # noqa: E501
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    alias = None
    quals = OrderedDict()
    ns = p.parser.target_namespace or p.parser.handle.default_namespace
    if isinstance(p[1], str):  # no qualifiers
        cname = p[3]
        if p[4] == '{':
            props = p[5]
        else:
            props = p[6]
            alias = p[4]
    else:
        cname = p[4]
        # quals = p[1]  # qualifiers on instances are deprecated -- rightly so.
        if p[5] == '{':
            props = p[6]
        else:
            props = p[7]
            alias = p[5]

    try:
        cc = p.parser.handle.GetClass(cname, namespace=ns, LocalOnly=False,
                                      IncludeQualifiers=True)
        try:
            p.parser.classnames[ns].append(cc.classname.lower())
        except KeyError:
            p.parser.classnames[ns] = [cc.classname.lower()]
    except CIMError as ce:
        if ce.status_code == CIM_ERR_NOT_FOUND:
            if p.parser.verbose:
                p.parser.log(
                    _format("Class {0!A} does not exist", cname))
            file_ = p.parser.mofcomp.find_mof(cname)
            if not file_:
                if p.parser.verbose:
                    p.parser.log("Can't find file to satisfy class")
                raise MOFDependencyError(
                    msg=_format(
                        "Cannot compile instance of {0!A} because its class "
                        "does not exist in the CIM repository and a MOF file "
                        "for that class cannot be found on the search path",
                        cname),
                    parser_token=p)
            p.parser.mofcomp.compile_file(file_, ns)
            cc = p.parser.handle.GetClass(cname, namespace=ns, LocalOnly=False,
                                          IncludeQualifiers=True)
        else:
            raise MOFRepositoryError(
                msg=_format(
                    "Cannot compile instance of {0!A} because the CIM "
                    "repository returned an error for GetClass",
                    cname),
                parser_token=p,
                cim_error=ce)

    inst = CIMInstance(cname, qualifiers=quals)

    for prop in props:
        pname = prop[1]
        pval = prop[2]
        try:
            cprop = cc.properties[pname]
        except KeyError:
            raise MOFDependencyError(
                msg=_format(
                    "Cannot compile instance of {0!A} because its "
                    "property {1!A} is not declared in the class",
                    cname, pname),
                parser_token=p)

        # confirm property name not duplicated.
        if pname in inst.properties:
            raise MOFParseError(
                msg=_format(
                    "Cannot compile instance of {0!A} because it specifies "
                    "property {1!A} more than once",
                    cname, pname),
                parser_token=p)

        try:
            # build instance property from class property but without
            # qualifiers, default value,
            pprop = cprop.copy()
            embedded_object_type = None
            allowed_types = None
            pprop.qualifiers = NocaseDict()
            # If embedded instance/object property, compile the value component
            # and put into the property value.
            if 'EmbeddedInstance' in cprop.qualifiers:
                allowed_types = (CIMInstance,)
                embedded_object_type = "instance"
                # Issue: 2340: Extend to test with is_subclass from
                # base repository when that is committed
                # qclass = cprop.qualifiers['EmbeddedInstance'].value
                # if qclass:
                #   if not is_subclass(cprop, qclass):
                #       raise MOFDependencyError ...
            elif 'EmbeddedObject' in cprop.qualifiers:
                allowed_types = (CIMInstance,)
                embedded_object_type = "object"

            if embedded_object_type:
                if pval:
                    objs = p.parser.mofcomp.compile_embedded_value(pval, ns)
                    for obj in objs:
                        if not isinstance(inst, allowed_types):
                            cls_names = ", ".join([cl.__name__ for cl
                                                   in allowed_types])
                            raise MOFParseError(
                                msg=_format(
                                    "Property {0!A} with value {1!A} embedded "
                                    "object type must be ((1}). Actual type "
                                    "is {2}", cprop.name, cls_names, type(obj)))
                    # If the compile produces no objects there must have
                    # been an error or the compile was for some other
                    # object than the ones we want.
                    if not objs:
                        raise MOFParseError(
                            msg=_format(
                                "Property {0!A} with value {1!A} embedded"
                                " object compile produced no instances.",
                                cprop.name, pval))

                    # If array type insert list, else insert item 0 from list
                    pprop.value = objs if cprop.is_array else objs[0]
                    pprop.embedded_object = embedded_object_type
            else:
                if pval:
                    ival_is_array = isinstance(pval, list)
                    if cprop.is_array != ival_is_array:
                        raise MOFParseError(
                            msg=_format(
                                "Property {0!A} value {1!A} in instance of "
                                "class {2!A} has class and instance array "
                                "mismatch. The class definition is "
                                "array={3} instance value type is array={4} "
                                "for value type {5}",
                                pname, pval, cc.classname, cprop.is_array,
                                ival_is_array, type(pval)),
                            parser_token=p)
                pprop.value = cimvalue(pval, cprop.type)
            inst.properties[pname] = pprop
        except ValueError as ve:
            raise MOFParseError(
                msg=_format(
                    "Cannot compile instance of {0!A} because it specifies "
                    "property {1!A} with an invalid value {2!r}: {3}",
                    cname, pname, pval, ve),
                parser_token=p)

    # Returns the created instance and either the alias name or None
    # This allows the alias to be created from the CreateInstance
    # returned path rather than trying to build the path in the compiler.
    p[0] = [inst, alias]


def p_valueInitializerList(p):
    """valueInitializerList : valueInitializer
                            | valueInitializerList valueInitializer
                            """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]


def p_valueInitializer(p):
    """valueInitializer : identifier defaultValue ';'
                        | qualifierList identifier defaultValue ';'
                        """
    if len(p) == 4:
        id_ = p[1]
        val = p[2]
        quals = []
    else:
        quals = p[1]
        id_ = p[2]
        val = p[3]
    p[0] = (quals, id_, val)


def p_booleanValue(p):
    """booleanValue : FALSE
                    | TRUE
                    """
    p[0] = p[1].lower() == 'true'


def p_nullValue(p):
    """nullValue : NULL"""
    p[0] = None


def p_identifier(p):
    """identifier : IDENTIFIER
                  | ANY
                  | AS
                  | CLASS
                  | DISABLEOVERRIDE
                  | dataType
                  | ENABLEOVERRIDE
                  | FLAVOR
                  | INSTANCE
                  | METHOD
                  | OF
                  | PARAMETER
                  | PRAGMA
                  | PROPERTY
                  | QUALIFIER
                  | REFERENCE
                  | RESTRICTED
                  | SCHEMA
                  | SCOPE
                  | TOSUBCLASS
                  | TOINSTANCE
                  | TRANSLATABLE
    """
    p[0] = p[1]


def p_empty(p):
    'empty :'
    pass


def _lexpos(token):
    """
    Return the position in the (Lex or Yacc) token.
    """
    if isinstance(token, lex.LexToken):
        lexpos = token.lexpos
    else:
        assert isinstance(token, yacc.YaccProduction)
        lexpos = token.lexpos(1)  # always first item in grammar
    assert isinstance(lexpos, int)
    return lexpos


def _value(token):
    """
    Return the value of the (Lex or Yacc) token.
    """
    if isinstance(token, lex.LexToken):
        value = token.value
    else:
        assert isinstance(token, yacc.YaccProduction)
        value = token[1]  # always first item in grammar
    return value


def _find_column(input_, token):
    """
    Find the column in file where error occured. This is taken from the
    position in the (Lex or Yacc) token, converted to the position on the
    current line by finding the previous EOL.
    """
    lexpos = _lexpos(token)
    i = lexpos
    while i > 0:
        if input_[i] == '\n':
            break
        i -= 1
    column = max(lexpos - i - 1, 0)
    return column


def _get_error_context(input_, token):
    """
        Build a context string that defines where on the line the defined
        error occurs.  This consists of the characters ^ at the position
        and for the length defined by the lexer position and token length
    """
    lexpos = _lexpos(token)
    try:
        line = input_[lexpos: input_.index('\n', lexpos)]
    except ValueError:
        line = input_[lexpos]

    i = max(input_.rfind('\n', 0, lexpos), 0)
    line = input_[i:lexpos] + line
    lines = [line.strip('\r\n')]
    col = lexpos - i
    while len(lines) < 5 and i > 0:
        end = i
        i = max(input_.rfind('\n', 0, i), 0)
        lines.insert(0, input_[i:end].strip('\r\n'))
    pointer = ''
    for dummy_ch in str(_value(token)):
        pointer += '^'
    pointline = ''
    i = 0
    while i < col - 1:
        if lines[-1][i].isspace():
            pointline += lines[-1][i]
            # otherwise, tabs complicate the alignment
        else:
            pointline += ' '
        i += 1
    lines.append(pointline + pointer)
    return lines


class BaseRepositoryConnection(metaclass=ABCMeta):
    """
    An abstract base class for implementing CIM repository connections (or an
    entire CIM repository) for use by the MOF compiler. This class defines the
    interface that is used by the :class:`~pywbem.MOFCompiler` class when it
    interacts with its associated CIM repository.

    Class :class:`~pywbem.MOFCompiler` invokes only the WBEM operations that
    are defined as methods on this class:

    * :meth:`EnumerateInstanceNames` - Enumerate the paths of CIM instances in
      the repository.
    * :meth:`CreateInstance` - Create a CIM instance in the repository.
    * :meth:`ModifyInstance` - Modify a CIM instance in the repository.
    * :meth:`DeleteInstance` - Delete a CIM instance in the repository.
    * :meth:`GetClass` - Retrieve a CIM class from the repository.
    * :meth:`ModifyClass` - Modify a CIM class in the repository.
    * :meth:`CreateClass` - Create a CIM class in the repository.
    * :meth:`DeleteClass` - Delete a CIM class in the repository.
    * :meth:`EnumerateQualifiers` - Enumerate CIM qualifier types in the
      repository.
    * :meth:`GetQualifier` - Retrieve a CIM qualifier type from the repository.
    * :meth:`SetQualifier` - Create or modify a CIM qualifier type in the
      repository.
    * :meth:`DeleteQualifier` - Delete a qualifier type from the repository.

    Raises:

      : Implementation classes should raise only exceptions derived from
        :exc:`~pywbem.Error` or use assert for methods that are not implemented.
        Other exceptions are considered programming
        errors.
    """

    # See below
    def _getns(self):
        """get namespace not implemented for BaseRepositoryConnection."""
        raise NotImplementedError

    # See below
    def _setns(self, value):
        """
        Function to set namespace. Not implemented for
        BaseRepositoryConnection
        """
        raise NotImplementedError

    # Ideally this property would be created via abstractproperty(), but then
    # Sphinx does not generate documentation for it. So we create it via
    # property() and raise NotImplementedError exceptions in the default
    # implementations of the getter/setter methods.
    default_namespace = property(
        _getns, _setns, None,
        """
        :term:`string`: The default repository namespace.

        This property is settable.
        """
    )

    @abstractmethod
    def EnumerateInstanceNames(self, *args, **kwargs):
        """
        Enumerate the instance paths of CIM instances in a namespace of the
        CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateInstanceNames`.
        """
        raise NotImplementedError

    @abstractmethod
    def CreateInstance(self, *args, **kwargs):
        """
        Create a CIM instance in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """
        raise NotImplementedError

    @abstractmethod
    def ModifyInstance(self, *args, **kwargs):
        """
        Modify a CIM instance in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.ModifyInstance`.
        """
        raise NotImplementedError

    @abstractmethod
    def DeleteInstance(self, *args, **kwargs):
        """
        Delete a CIM instance in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.DeleteInstance`.
        """
        raise NotImplementedError

    @abstractmethod
    def GetClass(self, *args, **kwargs):
        """
        Retrieve a CIM class in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def ModifyClass(self, *args, **kwargs):
        """
        Modify a CIM class in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.ModifyClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def CreateClass(self, *args, **kwargs):
        """
        Create a CIM class in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def DeleteClass(self, *args, **kwargs):
        """
        Delete a CIM class in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.DeleteClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def EnumerateQualifiers(self, *args, **kwargs):
        """
        Enumerate the CIM qualifier types in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """
        raise NotImplementedError

    @abstractmethod
    def GetQualifier(self, *args, **kwargs):
        """
        Retrieve a CIM qualifier type in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """
        raise NotImplementedError

    @abstractmethod
    def SetQualifier(self, *args, **kwargs):
        """
        Create or modify a CIM qualifier type in a namespace of the CIM
        repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """
        raise NotImplementedError

    @abstractmethod
    def DeleteQualifier(self, *args, **kwargs):
        """
        Delete a CIM qualifier type in a namespace of the CIM repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.DeleteQualifier`.
        """
        raise NotImplementedError


BaseRepositoryConnection.register(WBEMConnection)  # pylint: disable=no-member


class MOFWBEMConnection(BaseRepositoryConnection):
    """
    A CIM repository connection to an in-memory repository on top of an
    optional underlying WBEM connection.

    If a WBEM connection is provided with the conn parameter, that connection
    is the target for any operations that acquire CIM objects and the in-memory
    store acts as a cache for CIM qualifiers declarations, CIM Classes, and CIM
    Instances created and as a rollback log in support of rolling back the
    operations. This is the mode in which the MOF compiler uses this class.

    If the underlying WBEM connection is not provided, the in-memory repository
    acts as a CIM repository that is targeted by the operations. This mode is
    used for testing only.

    MOFWBEMConnection only implements the BaseRepositoryConnection
    methods required to implement the mof compiler rollback functionality.

    This class implements the
    :class:`~pywbem.BaseRepositoryConnection` interface.

    This implementation sets the path component of instances created including
    keybindings using property values in the instance. It does NOT confirm that
    all key properties are included in the path.

    Raises:

      : The methods of this class may raise any exceptions described for
        class :class:`~pywbem.WBEMConnection`.
    """

    def __init__(self, conn=None):
        """
        Parameters:

          conn (BaseRepositoryConnection):
            The underlying repository connection.

            `None` means that there is no underlying repository and all
            operations performed through this object will fail.
        """

        self.conn = conn
        self.conn_id = conn.conn_id if conn is not None else None
        self.class_names = {}
        self.qualifiers = {}
        self.instances = {}
        self.classes = {}
        self.compile_ordered_classnames = []
        if conn is None:
            # This attribute is used only to make get/set
            # of 'default_namespace' behave as it should, in the case
            # of conn=None.
            self.__default_namespace = 'root/cimv2'

    def _getns(self):
        """
        :term:`string`: Return the default repository namespace to be used.

        This method exists for compatibility. Use the :attr:`default_namespace`
        property instead.
        """
        if self.conn is not None:
            return self.conn.default_namespace
        return self.__default_namespace

    def _setns(self, value):
        """
        Set the default repository namespace to be used.

        This method exists for compatibility. Use the :attr:`default_namespace`
        property instead.
        """
        if self.conn is not None:
            self.conn.default_namespace = value
        else:
            self.__default_namespace = value

    getns = _getns  # for compatibility
    setns = _setns  # for compatibility

    default_namespace = property(
        _getns, _setns, None,
        """
        :term:`string`: The default repository namespace to be used.

        The default repository namespace is the default namespace of the
        underlying repository connection if there is such an underlying
        connection, or the default namespace of this object.

        Initially, the default namespace of this object is 'root/cimv2'.

        This property is settable. Setting it will cause the default namespace
        of the underlying repository connection to be updated if there is such
        an underlying connection, or the default namespace of this object.
        """
    )

    def EnumerateInstanceNames(self, *args, **kwargs):
        """This method is used by the MOF compiler only when it creates a
        namespace in the course of handling CIM_ERR_NAMESPACE_NOT_FOUND.
        Because the operations of this class silently create every namespace
        that is needed and never return that error, this method is never
        called, and is therefore not implemented.
        """

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def ModifyInstance(self, *args, **kwargs):
        """This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to create an instance.
        Because :meth:`CreateInstance` overwrites existing instances, this
        method is never called, and is therefore not implemented.
        NOTE: This error means that the mof compiler logic to attempt
        modifyinstance if createinstance fails does not attempt the
        modifyinstance.
        """

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def CreateInstance(self, *args, **kwargs):
        """
        Create a CIM instance in the local repository of this class. This
        implementation does not test for duplicate instances but appends
        each new instance to the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """

        inst = args[0] if args else kwargs['NewInstance']
        ns = kwargs.get('namespace', self.default_namespace)

        # If the path or keybindings do not exist, create the path from
        # the class and instance and set it into NewInstance
        if not inst.path or not inst.path.keybindings:
            cls = self.GetClass(inst.classname,
                                namespace=ns,
                                LocalOnly=False,
                                IncludeQualifiers=True)
            inst.path = CIMInstanceName.from_instance(
                cls, inst, namespace=ns)

        if "Abstract" in cls.qualifiers:
            warnings.warn(
                _format("Tolerating instance creation of abstract class {0} "
                        " in namepace {1} which is forbidden by DMTF DSP0004.",
                        inst.classname, ns),
                ToleratedSchemaIssueWarning, 1)

        try:
            self.instances[ns].append(inst)
        except KeyError:  # namespace ns does not exist. Create it
            self.instances[ns] = [inst]
        return inst.path

    def DeleteInstance(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def GetClass(self, *args, **kwargs):
        """Retrieve a CIM class from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """

        cname = args[0] if args else kwargs['ClassName']
        ns = kwargs.get('namespace', self.default_namespace)

        try:
            cc = self.classes[ns][cname]
        except KeyError:
            if self.conn is None:
                ce = CIMError(CIM_ERR_NOT_FOUND, cname)
                raise ce
            cc = self.conn.GetClass(*args, **kwargs)
            try:
                self.classes[ns][cc.classname] = cc
            except KeyError:
                self.classes[ns] = NocaseDict({cc.classname: cc})
        if 'LocalOnly' in kwargs and not kwargs['LocalOnly']:
            if cc.superclass:
                try:
                    del kwargs['ClassName']
                except KeyError:
                    pass
                if args:
                    args = args[1:]
                super_ = self.GetClass(cc.superclass, *args, **kwargs)
                for prop in super_.properties.values():
                    if prop.name not in cc.properties:
                        cc.properties[prop.name] = prop
                for meth in super_.methods.values():
                    if meth.name not in cc.methods:
                        cc.methods[meth.name] = meth
        return cc

    def ModifyClass(self, *args, **kwargs):  # pylint: disable=no-self-use
        """This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to create a class.
        Because :meth:`CreateClass` overwrites existing classes, this method
        is never called, and is therefore not implemented.
        """

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def CreateClass(self, *args, **kwargs):
        """Create a CIM class in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """

        cc = args[0] if args else kwargs['NewClass']
        ns = kwargs.get('namespace', self.default_namespace)
        cc_path = CIMClassName(namespace=ns, classname=cc.classname)

        if cc.superclass:
            try:
                # Since this may cause additional GetClass calls
                # IncludeQualifiers = True insures reference properties on
                # instances with aliases get built correctly.
                self.GetClass(cc.superclass, namespace=ns, LocalOnly=True,
                              IncludeQualifiers=True)
            except CIMError as ce:
                if ce.status_code == CIM_ERR_NOT_FOUND:
                    raise CIMError(
                        CIM_ERR_INVALID_SUPERCLASS,
                        _format("Cannot create class {0} because its "
                                "superclass {1!A} does not exist",
                                cc_path, cc.superclass),
                        conn_id=self.conn_id)
                raise

        self.compile_ordered_classnames.append(cc.classname)

        # Class created in local repo before tests because that allows
        # tests that may actually include this class to succeed in
        # the test code below.
        this_ns = ns
        try:
            # The following generates an exception for each new ns
            self.classes[this_ns][cc.classname] = cc
        except KeyError:
            self.classes[this_ns] = NocaseDict({cc.classname: cc})

        objects = list(cc.properties.values())
        for meth in cc.methods.values():
            objects += list(meth.parameters.values())

        for obj in objects:
            # Validate that reference_class exists in repo
            if obj.type == 'reference':
                try:
                    self.GetClass(obj.reference_class, namespace=ns,
                                  LocalOnly=True,
                                  IncludeQualifiers=True)
                except CIMError as ce:
                    if ce.status_code == CIM_ERR_NOT_FOUND:
                        raise CIMError(
                            CIM_ERR_INVALID_PARAMETER,
                            _format("Cannot create class {0} because class "
                                    "{1!A} referenced by its element {2!A} "
                                    "does not exist",
                                    cc_path, obj.reference_class, obj.name),
                            conn_id=self.conn_id)
                    # NOTE: Only delete when this is total failure
                    del self.classes[this_ns][cc.classname]
                    raise

            elif obj.type == 'string':
                if 'EmbeddedInstance' in obj.qualifiers:
                    eiqualifier = obj.qualifiers['EmbeddedInstance']
                    # The DMTF spec allows the value to be None
                    if eiqualifier.value is None:
                        continue
                    try:
                        self.GetClass(eiqualifier.value, namespace=ns,
                                      LocalOnly=True,
                                      IncludeQualifiers=False)
                    except CIMError as ce:
                        if ce.status_code == CIM_ERR_NOT_FOUND:
                            raise CIMError(
                                CIM_ERR_INVALID_PARAMETER,
                                _format("Cannot create class {0} because class "
                                        "{1!A} specified by the "
                                        "EmbeddedInstance qualifier on its "
                                        "element {2!A} does not exist",
                                        cc_path, eiqualifier.value, obj.name),
                                conn_id=self.conn_id)
                        # Only delete when total failure
                        del self.classes[this_ns][cc.classname]
                        raise

        # Issue #991: CreateClass should reject if the class already exists

        # Add the classname to the local class_names dictionary used by
        # rollback
        try:
            self.class_names[this_ns].append(cc.classname)
        except KeyError:
            self.class_names[this_ns] = [cc.classname]

    def DeleteClass(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def EnumerateQualifiers(self, *args, **kwargs):
        """Enumerate the qualifier types in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        ns = kwargs.get('namespace', self.default_namespace)

        if self.conn is not None:
            rv = self.conn.EnumerateQualifiers(*args, **kwargs)
        else:
            rv = []
        try:
            rv += list(self.qualifiers[ns].values())
        except KeyError:
            pass
        return rv

    def GetQualifier(self, *args, **kwargs):
        """Retrieve a qualifier type from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """

        qualname = args[0] if args else kwargs['QualifierName']
        ns = kwargs.get('namespace', self.default_namespace)

        try:
            qual = self.qualifiers[ns][qualname]
        except KeyError:
            if self.conn is None:
                raise CIMError(
                    CIM_ERR_NOT_FOUND, qualname, conn_id=self.conn_id)
            qual = self.conn.GetQualifier(*args, **kwargs)
        return qual

    def SetQualifier(self, *args, **kwargs):
        """Create or modify a qualifier type in the local repository of this
        class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """

        qual = args[0] if args else kwargs['QualifierDeclaration']
        ns = kwargs.get('namespace', self.default_namespace)

        try:
            self.qualifiers[ns][qual.name] = qual
        except KeyError:
            self.qualifiers[ns] = NocaseDict({qual.name: qual})

    def DeleteQualifier(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(
            CIM_ERR_FAILED, 'This should not happen!',
            conn_id=self.conn_id)

    def rollback(self, verbose=False):
        """
        Remove classes and instances from the underlying repository, that have
        been created in the local repository of this class.

        Limitations:

        1. At this point, only classes and instances will be removed,
        but not qualifiers.

        2. This may not work with instances created by other means, ex.
        other mof_compilers because of amgiguity in the definition of
        instance names for associations (ex. The namespace component
        in reference properties)

        3. This only removes the classes specifically defined in the compiled
        mof and not any classes installed as prerquisits as part of the
        compile (ex. superclasses, classes defined by references)
        """
        for ns, insts in self.instances.items():
            insts.reverse()
            for inst in insts:
                try:
                    if verbose:
                        print(_format("Deleting instance {0}", inst.path))
                    self.conn.DeleteInstance(inst.path)
                except CIMError as ce:
                    print(_format("Error deleting instance {0}", inst.path))
                    print(_format("     {0} {1}",
                                  ce.status_code, ce.status_description))
        for ns, cnames in self.class_names.items():
            self.default_namespace = ns
            cnames.reverse()
            for cname in cnames:
                classpath = CIMClassName(namespace=ns, classname=cname)
                try:
                    if verbose:
                        print(_format("Deleting class {0}", classpath))
                    self.conn.DeleteClass(cname)
                except CIMError as ce:
                    print(_format("Error deleting class {0}", classpath))
                    print(_format("     {0} {1}",
                                  ce.status_code, ce.status_description))
        # Issue #990: Also roll back changes to qualifier declarations


def _print_logger(msg):
    """Print the `msg` parameter to stdout."""
    print(msg)


class MOFCompiler:
    """
    A MOF compiler. See :ref:`MOF Compiler` for an explanation of MOF
    compilers in general.

    A MOF compiler may be associated with one CIM repository. The repository is
    used for looking up dependent CIM elements (e.g. the superclass specified
    in a class whose MOF definition is being compiled), and it is also updated
    with the result of the compilation. A repository contains CIM namespaces,
    and the namespaces contain CIM classes, instances and qualifier types.

    The association of a MOF compiler with a CIM repository is established when
    creating an object of this class. The interactions with the CIM repository
    are defined in the abstract base class
    :class:`~pywbem.BaseRepositoryConnection`.
    """

    def __init__(self, handle, search_paths=None, verbose=False,
                 log_func=_print_logger):
        # pylint: disable=line-too-long
        """
        Parameters:

          handle (BaseRepositoryConnection or :class:`~pywbem.WBEMConnection`):
            A handle identifying the CIM repository that will be associated
            with the MOF compiler.

            If the provided object is a repository connection (i.e. derived
            from :class:`BaseRepositoryConnection`, typically that would be a
            :class:`~pywbem.MOFWBEMConnection` object), it is directly used
            by the MOF compiler to interface with the repository.

            If the provided object is a WBEM connection (i.e.
            :class:`~pywbem.WBEMConnection` or
            :class:`~pywbem_mock.FakedWBEMConnection`),  the MOF compiler
            connects directly to interface defined by handle.

            `None` means that no CIM repository will be associated. In this
            case, the MOF compiler can only process standalone MOF that does
            not depend on existing CIM elements in the repository.

          search_paths (:term:`py:iterable` of :term:`string` or :term:`string`):
            Directory path name(s) where the MOF compiler will search for MOF
            dependent files if the MOF element they define is not in the target
            namespace of the CIM repository. The compiler searches the
            specified directories and their subdirectories.

            MOF dependent files are:

            * The MOF file defining the superclass of a class that is compiled.
              The MOF file searched for is '<classname>.mof'.

            * The MOF file defining the qualifier type of a qualifier that
              is specified on a MOF element that is compiled.
              The MOF files searched for are 'qualifiers.mof' and
              'qualifiers_optional.mof'.

            * The MOF file of a class specified in a reference property or
              in the `EmbeddedInstance` qualifier that is compiled.
              The MOF file searched for is '<classname>.mof'.
              This is only partly implemented, see issue #1138.

            Note that MOF include files are not searched for; they are specified
            in the ``pragma include`` directive as a file path relative to the
            including file.

          verbose (:class:`py:bool`):
            Indicates whether to issue more detailed compiler messages.

          log_func (:term:`callable`):
            A logger function that is invoked for each compiler message.
            The logger function must take one parameter of string type
            (byte string or unicode string).
            The default logger function prints to stdout.
            If `None`, compiler messages are not logged.
        """  # noqa: E501

        if isinstance(handle, WBEMConnection):
            conn = handle  # handle will be the WBEMConnection object
        elif handle is None:
            # The compiler needs a place to store compiled elements, so it
            # gets a local-only MOFWBEMConnection in this case.
            handle = MOFWBEMConnection(conn=None)
            conn = None
        elif isinstance(handle, BaseRepositoryConnection):
            conn = getattr(handle, 'conn', None)
            if conn and not isinstance(conn, WBEMConnection):
                raise TypeError(
                    _format("If the handle parameter is a CIM repository "
                            "connection its conn attribute must be None "
                            "or WBEMConnection, but it is: {0}", type(conn)))
        else:
            raise TypeError(
                _format("The handle parameter must be either a CIM repository "
                        "connection (derived from BaseRepositoryConnection) "
                        "or a WBEM connection (WBEMConnection), but is: {0}",
                        type(handle)))

        server = WBEMServer(conn) if conn else None

        if search_paths is None:
            search_paths = []
        elif isinstance(search_paths, str):
            search_paths = [search_paths]
        elif not isinstance(search_paths, (list, tuple)):
            raise TypeError(
                _format("search_paths parameter must be list or tuple, but "
                        "is: {0}", type(search_paths)))

        self.conn = conn  # Only used for closing it.
        self._log_func = log_func

        self.parser = _yacc(verbose)

        self.parser.search_paths = search_paths
        self.handle = handle
        self.parser.handle = handle
        self.server = server
        self.parser.server = server
        self.lexer = _lex(verbose)
        self.lexer.parser = self.parser
        self.lexer.last_msg = None
        self.parser.qualcache = {}
        self.parser.classnames = {}
        if handle:
            default_namespace = handle.default_namespace
            self.parser.qualcache[default_namespace] = NocaseDict()
            self.parser.classnames[default_namespace] = []
        self.parser.mofcomp = self
        self.parser.verbose = verbose
        self.parser.aliases = {}
        self.parser.log = self._log
        # Set by compile_string to define the namespace used by the compiler
        # for the current compilation
        self.parser.target_namespace = None

        # Target for output of embedded instances and embedded classes when
        # not None.
        self.parser.embedded_objects = None

    def conn_close(self):
        """
        Close the underlying connection, if it is a WBEMConnection.
        """
        if isinstance(self.conn, WBEMConnection):
            self.conn.close()

    def _log(self, msg):
        """
        Log a MOF compiler error message to the destination that was set
        with the ``log_func`` argument when creating the
        :class:`~pywbem.MOFCompiler` object.
        """
        if self._log_func:
            self._log_func(_ensure_unicode(msg))

    def compile_embedded_value(self, mof, ns, filename=None):
        """
        Compile a string of MOF statements that must represent one or
        CIMInstance objects and save the resulting CIMInstance(s) in a known
        variable. Thiis method in conjunction with the compiler does not put
        the compiled instances into the repository but returns them to the user.

        Parameters:

          mof (:term:`string` or list of :term:`string`):
            The string or list of strings MOF statements to be compiled.

          ns (:term:`string`):
            The name of the CIM namespace in the associated CIM repository
            that is used for lookup of any dependent CIM elements, and that
            is also the target of the compilation. If `None`, the default
            namespace of the connection is used. The namespace specified in
            this parameter must exist.

          filename (:term:`string`):
            The path name of the file that the MOF statements were read from.
            This information is used only in compiler messages.

        Raises:

          MOFCompileError: Error compiling the MOF.
        """
        lexer = self.lexer.clone()
        lexer.parser = self.parser
        # Save any previous parser.file and parser.mof to restore when
        # this compile successful. Since they are not defined in the __init__
        # use try block to construct them

        # save the file and mof attributes to be restored later.
        # si
        try:
            oldfile = self.parser.file
        except AttributeError:
            oldfile = None
        self.parser.file = filename
        try:
            oldmof = self.parser.mof
        except AttributeError:
            oldmof = None
        self.parser.mof = mof

        # The client operations would automatically use the connection's
        # default namespace if we passed `None`. However, in order to show
        # the default namespace in compiler messages, we apply the defaulting
        # here.
        if not ns:
            ns = self.handle.default_namespace

        # Save the namespace parameter in variable known to the parser.
        if self.parser.verbose:
            self.parser.log(
                _format("Target namespace {0!A}", ns))
        self.parser.target_namespace = ns

        if ns not in self.parser.qualcache:
            self.parser.qualcache[ns] = NocaseDict()
        if ns not in self.parser.classnames:
            self.parser.classnames[ns] = []

        try:
            # Set this variable to list to short-circuit insertion of created
            # classes and instances to this list rather than to the repository
            self.parser.embedded_objects = []
            # Call the parser.  To generate detailed output of states
            # add debug=... to following line where debug may be a
            # constant (ex. 1) or may be a log definition, ex..
            # log = logging.getLogger()
            # logging.basicConfig(level=logging.DEBUG)
            if isinstance(mof, list):
                for mof_str in mof:
                    self.parser.mof = mof_str
                    _ = self.parser.parse(mof_str, lexer=lexer)
            else:
                self.parser.mof = mof
                _ = self.parser.parse(mof, lexer=lexer)

            self.parser.file = oldfile
            self.parser.mof = oldmof
            return self.parser.embedded_objects
        except MOFCompileError as pe:
            # Generate the error message into log and reraise error
            self.parser.log(pe.get_err_msg())
            raise
        finally:
            # Force the embedded_iobjects variable to be reset telling the
            # compiler not to insert new objects into this variable
            self.parser.embedded_objects = None

    def compile_string(self, mof, ns, filename=None):
        """
        Compile a string of MOF statements into a namespace of the associated
        CIM repository.

        Parameters:

          mof (:term:`string`):
            The string of MOF statements to be compiled.

          ns (:term:`string`):
            The name of the CIM namespace in the associated CIM repository that
            is the target of the compilation, and is also used for lookup of any
            dependent CIM elements. If `None`, the default namespace of the
            connection is used. A namespace defined in a MOF '#pragma namespace'
            directive supersedes this namespace from the point in the
            compilation unit(string/file) where it is declared. The namespace
            specified in this parameter or in the MOF '#pragma namespace'
            directive must exist.

          filename (:term:`string`):
            The path name of the file that the MOF statements were read from.
            This information is used only in compiler messages.

        Raises:

          MOFCompileError: Error compiling the MOF.
        """
        lexer = self.lexer.clone()
        lexer.parser = self.parser

        # Save any previous parser.file and parser.mof to restore when
        # this compile successful
        try:
            oldfile = self.parser.file
        except AttributeError:
            oldfile = None
        self.parser.file = filename
        try:
            oldmof = self.parser.mof
        except AttributeError:
            oldmof = None
        self.parser.mof = mof

        # The client operations would automatically use the connection's
        # default namespace if we passed `None`. However, in order to show
        # the default namespace in compiler messages, we apply the defaulting
        # here.
        if not ns:
            ns = self.handle.default_namespace

        # Save the namespace parameter in variable known to the parser.
        if self.parser.verbose:
            self.parser.log(
                _format("Target namespace {0!A}", ns))
        self.parser.target_namespace = ns

        if ns not in self.parser.qualcache:
            self.parser.qualcache[ns] = NocaseDict()
        if ns not in self.parser.classnames:
            self.parser.classnames[ns] = []

        try:
            # Call the parser.  To generate detailed output of states
            # add debug=... to following line where debug may be a
            # constant (ex. 1) or may be a log definition, ex..
            # log = logging.getLogger()
            # logging.basicConfig(level=logging.DEBUG)
            rv = self.parser.parse(mof, lexer=lexer)
            self.parser.file = oldfile
            self.parser.mof = oldmof
            return rv
        except MOFCompileError as pe:
            # Generate the error message into log and reraise error
            self.parser.log(pe.get_err_msg())
            raise

    def compile_file(self, filename, ns):
        """
        Compile a MOF file into a namespace of the associated CIM repository.

        Parameters:

          filename (:term:`string`):
            The path name of the MOF file containing the MOF statements to be
            compiled.

          ns (:term:`string`):
            The name of the CIM namespace in the associated CIM repository that
            is the target of the compilation, and is also used for lookup of any
            dependent CIM elements. If `None`, the default namespace of the
            connection is used. A namespace defined in a namespace pragma of
            the MOF superceeds this namespace from the point in the
            compilation unit(string/file) where it is declared.  The namespace
            specified in this parameter or the MOF inamespace pragma must
            exist.

        Raises:

          IOError: MOF file not found.
          MOFCompileError: Error compiling the MOF.
        """
        if self.parser.verbose:
            self.parser.log(
                _format("Compiling file {0!A}", filename))

        if not os.path.exists(filename):
            # try to find in search path
            rfilename = self.find_mof(os.path.basename(filename[:-4]).lower())
            if rfilename is None:
                raise OSError(
                    _format("No such file: {0!A}", filename))
            filename = rfilename
        with open(filename, encoding='utf-8') as f:
            mof = f.read()

        return self.compile_string(mof, ns, filename=filename)

    def find_mof(self, classname):
        """
        Find the MOF file that defines a particular CIM class, in the search
        path of the MOF compiler.

        The MOF file is found based on its file name: It is assumed that the
        base part of the file name is the CIM class name.

        Example: The class "CIM_ComputerSystem" is expected to be in a file
        "CIM_ComputerSystem.mof".

        Parameters:

          classame (:term:`string`):
            The name of the CIM class to look up.

        Returns:

          :term:`string`: Path name of the MOF file defining the CIM class, if
          it was found. `None`, if it was not found.
        """

        classname = classname.lower()
        for search in self.parser.search_paths:
            for root, dummy_dirs, files in os.walk(search):
                for file_ in files:
                    if file_.endswith('.mof') and \
                            file_[:-4].lower() == classname:
                        return os.path.join(root, file_)
        return None

    def rollback(self, verbose=False):
        """
        Rollback any changes to the CIM repository that were performed by
        compilations using this MOF compiler object, since the object was
        created.
        """

        self.handle.rollback(verbose=verbose)


def _build(verbose=False, out_dir=_tabdir):
    """
    Build the LEX and YACC table modules for the MOF compiler, if they do
    not exist yet, or if their table versions do not match the installed
    version of the `ply` package.
    """

    if verbose:
        print(
            _format("Building LEX/YACC modules for MOF compiler in: {0}",
                    out_dir))

    _yacc(verbose, out_dir=out_dir)
    _lex(verbose, out_dir=out_dir)


def _yacc(verbose=False, out_dir=None):
    """
    Return YACC parser object for the MOF compiler.

    Parameters:

      verbose (bool): Print messages while creating the parser object.

      out_dir (string): Path name of the directory in which the YACC table
        module source file (_mofparsetab.py) for the MOF compiler will be
        generated. If None, that file will not be generated.

    Returns:

      yacc.Parser: YACC parser object for the MOF compiler.

    Raises:
      MOFCompilerSetupError: Error creating the YACC parser.
    """

    # The write_tables argument controls whether the YACC parser writes
    # the YACC table module file.
    write_tables = (out_dir is not None)

    # In yacc(), the 'debug' parameter controls the main error
    # messages to the 'errorlog' in addition to the debug messages
    # to the 'debuglog'. Because we want to see the error messages,
    # we enable debug but set the debuglog to the NullLogger.
    # To enable debug logging, set debuglog to some other logger
    # (ex. PlyLogger(sys.stdout) to generate log output.
    # The 'module' argument needed to be passed to support Cython. Without it,
    # the default way of determining it skipps the cythonized call levels,
    # resulting in an incorrect module and subsequently to an error
    # message "ERROR: No token list is defined" and
    # an exception YaccError("Unable to build parser").

    log_stream = io.StringIO()
    try:
        parser = yacc.yacc(
            optimize=_optimize, tabmodule=_tabmodule, module=_module,
            outputdir=out_dir, write_tables=write_tables, debug=verbose,
            debuglog=yacc.NullLogger(), errorlog=yacc.PlyLogger(log_stream))
    except yacc.YaccError as exc:
        raise MOFCompilerSetupError(f"{exc}: {log_stream.getvalue()}")
    if verbose:
        print(log_stream.getvalue())
    return parser


def _lex(verbose=False, out_dir=None):
    """
    Return LEX analyzer object for the MOF Compiler.

    Parameters:

      verbose (bool): Print messages while creating the parser object.

      out_dir (string): Path name of the directory in which the LEX table
        module source file (_moflextab.py) for the MOF compiler will be
        generated. If None, that file will not be generated.

    Returns:

      lex.Lexer: LEX analyzer object for the MOF compiler.

    Raises:
      MOFCompilerSetupError: Error creating the LEX scanner.
    """

    # Unfortunately, lex() does not support a write_tables argument. It
    # always tries to write the tables if optimize=True, so we supply a dummy
    # output directory. Always setting optimize=False is also not a good
    # solution because that causes the input table not to be used.
    if out_dir is None:
        out_dir = tempfile.gettempdir()

    # To debug lex you may set debug=True and enable the debuglog statement.
    # or other logger definition.

    log_stream = io.StringIO()
    try:
        lexer = lex.lex(
            optimize=_optimize, lextab=_lextab, module=_module,
            outputdir=out_dir, debug=False,
            # debuglog=lex.PlyLogger(sys.stdout),
            errorlog=yacc.PlyLogger(log_stream))
    except SyntaxError as exc:
        raise MOFCompilerSetupError(f"{exc}: {log_stream.getvalue()}")
    if verbose:
        print(log_stream.getvalue())
    return lexer
