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
The language in which CIM classes are specified, is called `MOF` (for Managed
Object Format). It is defined in :term:`DSP0004`.

The pywbem package includes a MOF compiler.

MOF compilers take MOF files as input, compile them and the result is used to
update a target CIM repository. The repository may initially be empty, or may
contain the result of earlier MOF compilations that are used to resolve
dependencies the new MOF compilation may have.

The MOF compiler in this package also has an option to remove CIM elements
from the repository it has a definition for in the MOF files it processes.

The MOF compiler API provides for invoking the MOF compiler and for plugging in
your own CIM repository into the MOF compiler.

The MOF compiler API is available in the ``pywbem.mof_compiler`` module.

This chapter has the following sections:

* :ref:`MOFCompiler` - Describes the :class:`~pywbem.mof_compiler.MOFCompiler`
  class, which allows invoking the MOF compiler programmatically.

* :ref:`Repository connections` - Describes the
  :class:`~pywbem.mof_compiler.BaseRepositoryConnection` class that defines
  the interface for connecting to a CIM repository, and the
  :class:`~pywbem.mof_compiler.MOFWBEMConnection` class that is a connection
  to an in-memory repository on top of an underlying repository, and is used
  by the MOF compiler to provide rollback support.

* :ref:`Exceptions <MOF compiler exceptions>` - Describes the exceptions
  that can be raised by the MOF compiler, in addition to the exceptions
  that can be raised by the :ref:`WBEM client library API`.
"""

from __future__ import print_function, absolute_import

import sys
import os
import re
from abc import ABCMeta, abstractmethod

import six
from ply import yacc, lex

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMProperty, \
    CIMMethod, CIMParameter, CIMQualifier, CIMQualifierDeclaration, \
    NocaseDict, tocimobj
from .cim_operations import WBEMConnection
from .cim_constants import CIM_ERR_NOT_FOUND, CIM_ERR_FAILED, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_NAMESPACE, \
    CIM_ERR_INVALID_SUPERCLASS, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_INVALID_CLASS, _statuscode2string
from .exceptions import Error, CIMError

__all__ = ['MOFParseError', 'MOFWBEMConnection', 'MOFCompiler',
           'BaseRepositoryConnection']

# The following pylint is applied for the complete file because invalid
# names are used throughout the file and about 200 flags generated if
# this is not applied and at least some # may be part of ply rules.

# pylint: disable=invalid-name

_optimize = 1
_tabmodule = 'mofparsetab'
_lextab = 'moflextab'

# Directory for _tabmodule and _lextab
_tabdir = os.path.dirname(os.path.abspath(__file__))

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
# http://www.dabeaz.com/ply/ply.html#ply_nn6
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

utf8Char = r'(%s)|(%s)|(%s)|(%s)|(%s)|(%s)|(%s)|(%s)' % \
           (utf8_2, utf8_3_1, utf8_3_2, utf8_3_3, utf8_3_4, utf8_4_1,
            utf8_4_2, utf8_4_3)


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
    return t


def t_hexValue(t):
    r'[+-]?0[xX][0-9a-fA-F]+'
    return t


def t_binaryValue(t):
    r'[+-]?[0-9]+[bB]'
    # We must match [0-9], and then check the validity of the binary number.
    # If we match [01], the invalid number "02" (not in binary range, leading
    # zeros not allowed for decimal) would match 'decimalValue' and only
    # the zero would be taken out.
    if re.search(r'[2-9]', t.value) is not None:
        msg = "Skipping invalid binary number '%s' in line %d" % \
            (t.value, t.lineno)
        try:
            msg += " col %d" % _find_column(t.lexer.parser.mof, t)
        except AttributeError:
            pass  # adding t.lexpos does not make too much sense
        t.lexer.parser.log(msg)
        t.type = 'error'
        t.lexer.skip(len(t.value))
    return t


def t_octalValue(t):
    r'[+-]?0[0-9]+'
    # We must match [0-9], and then check the validity of the octal number.
    # If we match [0-7], the invalid number "08" (not in octal range, leading
    # zeros not allowed for decimal) would match 'decimalValue' and only
    # the zero would be taken out, and the 8 would be another decimalValue.
    if re.search(r'[8-9]', t.value) is not None:
        msg = "Skipping invalid octal number '%s' in line %d" % \
            (t.value, t.lineno)
        try:
            msg += " col %d" % _find_column(t.lexer.parser.mof, t)
        except AttributeError:
            pass  # adding t.lexpos does not make too much sense
        t.lexer.parser.log(msg)
        t.type = 'error'
        t.lexer.skip(len(t.value))
    return t


# Matching for decimal must be at the end of the other numerics because of
# the 0. If not at the end, 0 would match at the begin of e.g. an octal value.
def t_decimalValue(t):
    r'[+-]?([1-9][0-9]*|0)'
    return t


simpleEscape = r"""[bfnrt'"\\]"""
hexEscape = r'x[0-9a-fA-F]{1,4}'
escapeSequence = r'[\\]((%s)|(%s))' % (simpleEscape, hexEscape)
cChar = r"[^'\\\n\r]|(%s)" % escapeSequence
sChar = r'[^"\\\n\r]|(%s)' % escapeSequence

charvalue_re = r"'(%s)'" % cChar


@lex.TOKEN(charvalue_re)
def t_charValue(t):
    return t


stringvalue_re = r'"(%s)*"' % sChar


@lex.TOKEN(stringvalue_re)
def t_stringValue(t):
    return t


identifier_re = r'([a-zA-Z_]|(%s))([0-9a-zA-Z_]|(%s))*' % (utf8Char, utf8Char)


@lex.TOKEN(identifier_re)
def t_IDENTIFIER(t):
    t.type = reserved.get(t.value.lower(), 'IDENTIFIER')
    return t


# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.linestart = t.lexpos
    return  # discard token


t_ignore = ' \r\t'


def t_error(t):
    """ Lexer error callback from PLY Lexer with token in error.
    """

    msg = "Skipping first character of invalid token '%s' in line %d" % \
        (t.value, t.lineno)
    try:
        msg += " col %d" % _find_column(t.lexer.parser.mof, t)
    except AttributeError:
        pass  # adding t.lexpos does not make too much sense
    t.lexer.parser.log(msg)
    t.lexer.skip(1)


class MOFParseError(Error):
    """
        Exception raised when MOF cannot be parsed correctly, e.g. for
        syntax errors. Derived from :exc:`~pywbem.Error`.
    """

    # pylint: disable=super-init-not-called
    def __init__(self, parser_token=None, msg=None):
        """
        Parameters:

          parser_token:
            PLY parser token for the error (that is, the ``p`` argument
            of a PLY parser function). This token contains information on
            the location of the error in the MOF file, which is copied
            into this object, and is accessible via properties.

          msg (:term:`string`):
            Message text supplied by the creator of the error
        """

        if parser_token is None:
            self.args = (None, None, None, None)
        else:
            mof_ = parser_token.lexer.parser.mof
            self.args = (parser_token.lineno,
                         _find_column(mof_, parser_token),
                         parser_token.lexer.parser.file,
                         _get_error_context(mof_, parser_token))
        self._msg = msg

    @property
    def lineno(self):
        """Line number in the MOF file where the error occurred."""
        return self.args[0]

    @property
    def column(self):
        """Position within the line where the error occurred."""
        return self.args[1]

    @property
    def file(self):
        """
        File name of the MOF file where the error occurred, as a
        :term:`string`.
        """
        return self.args[2]

    @property
    def context(self):
        """
        Context string that can be inserted when printing the error message.
        The context string consists of a first line with a segment of the MOF
        surrounding the error position, and a second line that uses the '^'
        character to indicate the token in error.
        """
        return self.args[3]

    @property
    def msg(self):
        """
        Message that may be part of the error, as a :term:`string`. Generally,
        this is produced when the actual error position is not known but may be
        added by some production errors.
        """
        return self._msg

    def __str__(self):
        ret_str = 'MOFParseError: '
        if self.lineno is not None:
            ret_str += '%s:%s: %smsg=%s\n%s' % \
                (self.file, self.lineno, self.column, self.msg, self.context)
        else:
            ret_str += '%s' % self.msg
        return ret_str

    def get_err_msg(self):
        """
        Return the MOF compiler error message as a :term:`string`, in the
        format (assuming all components are provided):

        ::

            Syntax error:<file>:<lineno>: <msg>
            <context - MOF segment>
            <context - location indicator>
        """
        ret_str = 'Syntax error:'
        if self.file is not None and self.lineno is not None:
            ret_str += '%s:%s:' % (self.file, self.lineno)
        if self.msg:
            ret_str += " %s" % self.msg
        if self.context is not None:
            ret_str += '\n'.join(self.context)
        return ret_str


def p_error(p):
    """
        YACC Error Callback from the parser.  The parameter is the token
        in error and contains information on the file and position of the
        error. If p is `None`, PLY is returning eof error.
    """

    if p is None:
        raise MOFParseError(msg='Unexpected end of file')

    raise MOFParseError(parser_token=p)


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


def _create_ns(p, handle, ns):
    """Create a namespace in the target connection based on the `handle`
       and `ns` parameters.
    """

    # Figure out the flavor of cim server
    cimom_type = None
    ns = ns.strip('/')
    try:
        inames = handle.EnumerateInstanceNames('__Namespace', namespace='root')
        inames = [x['name'] for x in inames]
        if 'PG_InterOp' in inames:
            cimom_type = 'pegasus'
    except CIMError as ce:
        if ce.args[0] != CIM_ERR_NOT_FOUND:
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise
    if not cimom_type:
        try:
            inames = handle.EnumerateInstanceNames('CIM_Namespace',
                                                   namespace='Interop')
            inames = [x['name'] for x in inames]
            cimom_type = 'proper'
        except CIMError as ce:
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise

    if not cimom_type:
        ce = CIMError(CIM_ERR_FAILED,
                      'Unable to determine CIMOM type')
        ce.file_line = (p.parser.file, p.lexer.lineno)
        raise ce
    if cimom_type == 'pegasus':
        # To create a namespace in Pegasus, create an instance of
        # __Namespace with  __Namespace.Name = '', and create it in
        # the target namespace to be created.
        inst = CIMInstance(
            '__Namespace',
            properties={'Name': ''},
            path=CIMInstanceName(
                '__Namespace',
                keybindings={'Name': ''},
                namespace=ns))
        try:
            handle.CreateInstance(inst)
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_ALREADY_EXISTS:
                ce.file_line = (p.parser.file, p.lexer.lineno)
                raise

    elif cimom_type == 'proper':
        inst = CIMInstance(
            'CIM_Namespace',
            properties={'Name': ns},
            path=CIMInstanceName(
                'CIM_Namespace',
                namespace='root',
                keybindings={'Name': ns}))
        handle.CreateInstance(inst)


def p_mp_createClass(p):
    """mp_createClass : classDeclaration
                      | assocDeclaration
                      | indicDeclaration
                      """

    # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    ns = p.parser.handle.default_namespace
    cc = p[1]
    try:
        fixedNS = fixedRefs = fixedSuper = False
        while not fixedNS or not fixedRefs or not fixedSuper:
            try:
                if p.parser.verbose:
                    p.parser.log('Creating class %s:%s' % (ns, cc.classname))
                p.parser.handle.CreateClass(cc)
                if p.parser.verbose:
                    p.parser.log('Created class %s:%s' % (ns, cc.classname))
                p.parser.classnames[ns].append(cc.classname.lower())
                break
            except CIMError as ce:
                ce.file_line = (p.parser.file, p.lexer.lineno)
                errcode = ce.args[0]
                if errcode == CIM_ERR_INVALID_NAMESPACE:
                    if fixedNS:
                        raise
                    if p.parser.verbose:
                        p.parser.log('Creating namespace ' + ns)
                    _create_ns(p, p.parser.handle, ns)
                    fixedNS = True
                    continue
                if not p.parser.search_paths:
                    raise
                if errcode == CIM_ERR_INVALID_SUPERCLASS:
                    if fixedSuper:
                        raise
                    moffile = p.parser.mofcomp.find_mof(cc.superclass)
                    if not moffile:
                        raise
                    p.parser.mofcomp.compile_file(moffile, ns)
                    fixedSuper = True
                elif errcode in [CIM_ERR_INVALID_PARAMETER,
                                 CIM_ERR_NOT_FOUND,
                                 CIM_ERR_FAILED]:
                    if fixedRefs:
                        raise
                    if not p.parser.qualcache[ns]:
                        for fname in ['qualifiers', 'qualifiers_optional']:
                            qualfile = p.parser.mofcomp.find_mof(fname)
                            if qualfile:
                                p.parser.mofcomp.compile_file(qualfile, ns)
                    if not p.parser.qualcache[ns]:
                        # can't find qualifiers
                        raise
                    objects = list(cc.properties.values())
                    for meth in cc.methods.values():
                        objects += list(meth.parameters.values())
                    dep_classes = []
                    for obj in objects:
                        if obj.type not in ['reference', 'string']:
                            continue
                        if obj.type == 'reference':
                            if obj.reference_class.lower() not in dep_classes:
                                dep_classes.append(obj.reference_class.lower())
                            continue
                        # else obj.type is 'string'
                        try:
                            embedded_inst = obj.qualifiers['embeddedinstance']
                        except KeyError:
                            continue
                        embedded_inst = embedded_inst.value.lower()
                        if embedded_inst not in dep_classes:
                            dep_classes.append(embedded_inst)
                        continue
                    for klass in dep_classes:
                        if klass in p.parser.classnames[ns]:
                            continue
                        try:
                            # don't limit it with LocalOnly=True,
                            # PropertyList, IncludeQualifiers=False, ...
                            # because of caching in case we're using the
                            # special WBEMConnection subclass used for
                            # removing schema elements
                            p.parser.handle.GetClass(klass,
                                                     LocalOnly=False,
                                                     IncludeQualifiers=True)
                            p.parser.classnames[ns].append(klass)
                        except CIMError:
                            moffile = p.parser.mofcomp.find_mof(klass)
                            if not moffile:
                                raise
                            p.parser.mofcomp.compile_file(moffile, ns)
                            p.parser.classnames[ns].append(klass)
                    fixedRefs = True
                else:
                    raise

    except CIMError as ce:
        ce.file_line = (p.parser.file, p.lexer.lineno)
        if ce.args[0] != CIM_ERR_ALREADY_EXISTS:
            raise
        if p.parser.verbose:
            p.parser.log('Class %s already exist.  Modifying...' % cc.classname)
        try:
            p.parser.handle.ModifyClass(cc, ns)
        except CIMError as ce:
            p.parser.log('Error Modifying class %s: %s, %s' %
                         (cc.classname, ce.args[0], ce.args[1]))


def p_mp_createInstance(p):
    """mp_createInstance : instanceDeclaration"""
    inst = p[1]
    if p.parser.verbose:
        p.parser.log('Creating instance of %s.' % inst.classname)
    try:
        p.parser.handle.CreateInstance(inst)
    except CIMError as ce:
        if ce.args[0] == CIM_ERR_ALREADY_EXISTS:
            if p.parser.verbose:
                p.parser.log('Instance of class %s already exist.  '
                             'Modifying...' % inst.classname)
            try:
                p.parser.handle.ModifyInstance(inst)
            except CIMError as ce:
                if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                    if p.parser.verbose:
                        p.parser.log('ModifyInstance not supported.  '
                                     'Deleting instance of %s: %s' %
                                     (inst.classname, inst.path))
                    p.parser.handle.DeleteInstance(inst.path)
                    if p.parser.verbose:
                        p.parser.log('Creating instance of %s.' %
                                     inst.classname)
                    p.parser.handle.CreateInstance(inst)
        else:
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise


def p_mp_setQualifier(p):
    """mp_setQualifier : qualifierDeclaration"""
    qualdecl = p[1]
    ns = p.parser.handle.default_namespace
    if p.parser.verbose:
        p.parser.log('Setting qualifier %s' % qualdecl.name)
    try:
        p.parser.handle.SetQualifier(qualdecl)
    except CIMError as ce:
        if ce.args[0] == CIM_ERR_INVALID_NAMESPACE:
            if p.parser.verbose:
                p.parser.log('Creating namespace ' + ns)
            _create_ns(p, p.parser.handle, ns)
            if p.parser.verbose:
                p.parser.log('Setting qualifier %s' % qualdecl.name)
            p.parser.handle.SetQualifier(qualdecl)
        elif ce.args[0] == CIM_ERR_NOT_SUPPORTED:
            if p.parser.verbose:
                p.parser.log('Qualifier %s already exists.  Deleting...' %
                             qualdecl.name)
            p.parser.handle.DeleteQualifier(qualdecl.name)
            if p.parser.verbose:
                p.parser.log('Setting qualifier %s' % qualdecl.name)
            p.parser.handle.SetQualifier(qualdecl)
        else:
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise
    p.parser.qualcache[ns][qualdecl.name] = qualdecl


def p_compilerDirective(p):
    """compilerDirective : '#' PRAGMA pragmaName '(' pragmaParameter ')'"""
    directive = p[3].lower()
    param = p[5]
    if directive == 'include':
        fname = param
        if len(os.path.dirname(p.parser.file)) != 0:
            fname = os.path.dirname(p.parser.file) + '/' + fname
        p.parser.mofcomp.compile_file(fname, p.parser.handle.default_namespace)
    elif directive == 'namespace':
        p.parser.handle.default_namespace = param
        if param not in p.parser.qualcache:
            p.parser.qualcache[param] = NocaseDict()

    p[0] = None


def p_pragmaName(p):
    """pragmaName : identifier"""
    p[0] = p[1]


def p_pragmaParameter(p):
    """pragmaParameter : stringValue"""
    p[0] = _fixStringValue(p[1])


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
    if isinstance(p[1], six.string_types):  # no class qualifiers
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
    # pylint: disable=redefined-variable-type
    quals = dict([(x.name, x) for x in quals])
    methods = {}
    props = {}
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


def p_assocDeclaration(p):
    # pylint: disable=line-too-long
    """assocDeclaration : '[' ASSOCIATION qualifierListEmpty ']' CLASS className '{' associationFeatureList '}' ';'
                        | '[' ASSOCIATION qualifierListEmpty ']' CLASS className superClass '{' associationFeatureList '}' ';'
                        | '[' ASSOCIATION qualifierListEmpty ']' CLASS className alias '{' associationFeatureList '}' ';'
                        | '[' ASSOCIATION qualifierListEmpty ']' CLASS className alias superClass '{' associationFeatureList '}' ';'
                        """  # noqa: E501
    aqual = CIMQualifier('ASSOCIATION', True, type='boolean')
    # TODO flavor trash.
    quals = [aqual] + p[3]
    p[0] = _assoc_or_indic_decl(quals, p)


def p_indicDeclaration(p):
    # pylint: disable=line-too-long
    """indicDeclaration : '[' INDICATION qualifierListEmpty ']' CLASS className '{' classFeatureList '}' ';'
                        | '[' INDICATION qualifierListEmpty ']' CLASS className superClass '{' classFeatureList '}' ';'
                        | '[' INDICATION qualifierListEmpty ']' CLASS className alias '{' classFeatureList '}' ';'
                        | '[' INDICATION qualifierListEmpty ']' CLASS className alias superClass '{' classFeatureList '}' ';'
                        """  # noqa: E501
    iqual = CIMQualifier('INDICATION', True, type='boolean')
    # TODO flavor trash.
    quals = [iqual] + p[3]
    p[0] = _assoc_or_indic_decl(quals, p)


def _assoc_or_indic_decl(quals, p):
    """(refer to grammer rules on p_assocDeclaration and p_indicDeclaration)"""
    superclass = None
    alias = None
    cname = p[6]
    if p[7] == '{':
        cfl = p[8]
    elif p[7][0] == '$':  # alias
        alias = p[7]
        if p[8] == '{':
            cfl = p[9]
        else:
            superclass = p[8]
            cfl = p[10]
    else:
        superclass = p[7]
        cfl = p[9]
    props = {}
    methods = {}
    for item in cfl:
        item.class_origin = cname
        if isinstance(item, CIMMethod):
            methods[item.name] = item
        else:
            props[item.name] = item
    quals = dict([(x.name, x) for x in quals])
    cc = CIMClass(cname, properties=props, methods=methods,
                  superclass=superclass, qualifiers=quals)
    if alias:
        p.parser.aliases[alias] = cc
    return cc


def p_qualifierListEmpty(p):
    """qualifierListEmpty : empty
                          | qualifierListEmpty ',' qualifier
                          """
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[3]]


def p_associationFeatureList(p):
    """associationFeatureList : empty
                              | associationFeatureList associationFeature
                              """
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]


def p_className(p):
    """className : identifier"""
    p[0] = p[1]


def p_alias(p):
    """alias : AS aliasIdentifier"""
    p[0] = p[2]


def p_aliasIdentifier(p):
    """aliasIdentifier : '$' identifier"""
    p[0] = '$%s' % p[2]


def p_superClass(p):
    """superClass : ':' className"""
    p[0] = p[2]


def p_classFeature(p):
    """classFeature : propertyDeclaration
                    | methodDeclaration
                    | referenceDeclaration
                    """
    p[0] = p[1]


def p_associationFeature(p):
    """associationFeature : classFeature"""
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
    ns = p.parser.handle.default_namespace
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
            quals = p.parser.handle.EnumerateQualifiers()
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                ce.file_line = (p.parser.file, p.lexer.lineno)
                raise
            _create_ns(p, p.parser.handle, ns)
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
        ce = CIMError(CIM_ERR_FAILED, 'Unknown Qualifier: %s' % qname)
        ce.file_line = (p.parser.file, p.lexer.lineno)
        raise ce

    flavors = _build_flavors(p[0], flavorlist, qualdecl)
    if qval is None:
        if qualdecl.type == 'boolean':
            qval = True
        else:
            qval = qualdecl.value  # default value
    else:
        qval = tocimobj(qualdecl.type, qval)
    p[0] = CIMQualifier(qname, qval, type=qualdecl.type, **flavors)
    # TODO propagated?


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


# TODO 8/16 ks Consider complete removed of TOINSTANCE from compiler
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
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], None, type=p[2], qualifiers=quals)


def p_propertyDeclaration_6(p):
    # pylint: disable=line-too-long
    """propertyDeclaration_6 : qualifierList dataType propertyName defaultValue ';'"""  # noqa: E501
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], tocimobj(p[2], p[4]),
                       type=p[2], qualifiers=quals)


def p_propertyDeclaration_7(p):
    """propertyDeclaration_7 : qualifierList dataType propertyName array ';'"""
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], None, type=p[2], qualifiers=quals,
                       is_array=True, array_size=p[4])


def p_propertyDeclaration_8(p):
    # pylint: disable=line-too-long
    """propertyDeclaration_8 : qualifierList dataType propertyName array defaultValue ';'"""  # noqa: E501
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], tocimobj(p[2], p[5]),
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
    # pylint: disable=redefined-variable-type
    quals = dict([(x.name, x) for x in quals])
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
    if isinstance(p[1], six.string_types):  # no quals
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
    # pylint: disable=redefined-variable-type
    params = dict([(param.name, param) for param in paramlist])
    quals = dict([(q.name, q) for q in quals])
    p[0] = CIMMethod(mname, return_type=dt, parameters=params,
                     qualifiers=quals)
    # note: class_origin is set when adding method to class.
    # TODO what to do with propagated?


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
    quals = dict([(x.name, x) for x in p[1]])
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
    quals = dict([(x.name, x) for x in p[1]])
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


def _fixStringValue(s):
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
            rv += chr(hexc)
            i += j - 1

        esc = False

    return rv


def p_stringValueList(p):
    """stringValueList : stringValue
                       | stringValueList stringValue
                       """
    if len(p) == 2:
        p[0] = _fixStringValue(p[1])
    else:
        p[0] = p[1] + _fixStringValue(p[2])


def p_constantValue(p):
    """constantValue : integerValue
                     | floatValue
                     | charValue
                     | stringValueList
                     | booleanValue
                     | nullValue
                     """
    p[0] = p[1]


def p_integerValue(p):
    """integerValue : binaryValue
                    | octalValue
                    | decimalValue
                    | hexValue
                    """
    p[0] = int(p[1])
    # TODO deal with non-decimal values.


def p_referenceInitializer(p):
    """referenceInitializer : objectHandle
                            | aliasIdentifier
                            """
    if p[1][0] == '$':
        try:
            p[0] = p.parser.aliases[p[1]]
        except KeyError:
            ce = CIMError(CIM_ERR_FAILED,
                          'Unknown alias: ' + p[1])
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce
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

    flavors = _build_flavors(p[0], flist)

    p[0] = CIMQualifierDeclaration(
        qualname, dt, value=value, is_array=is_array, array_size=array_size,
        scopes=scopes, **flavors)


def _build_flavors(p, flist, qualdecl=None):
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
    if ('disableoverride' in flist and 'enableoverride' in flist) \
        or \
        ('restricted' in flist and 'tosubclass' in flist):  # noqa: E125

        raise MOFParseError(parser_token=p, msg="Conflicting flavors are"
                            "invalid")

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
    """scope : ',' SCOPE '(' metaElementList ')'"""
    slist = p[4]
    scopes = {}
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


def p_metaElementList(p):
    """metaElementList : metaElement
                       | metaElementList ',' metaElement
                       """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_metaElement(p):
    """metaElement : SCHEMA
                   | CLASS
                   | ASSOCIATION
                   | INDICATION
                   | QUALIFIER
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
    quals = {}
    ns = p.parser.handle.default_namespace
    if isinstance(p[1], six.string_types):  # no qualifiers
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
        cc = p.parser.handle.GetClass(cname, LocalOnly=False,
                                      IncludeQualifiers=True)
        p.parser.classnames[ns].append(cc.classname.lower())
    except CIMError as ce:
        ce.file_line = (p.parser.file, p.lexer.lineno)
        if ce.args[0] == CIM_ERR_NOT_FOUND:
            file_ = p.parser.mofcomp.find_mof(cname)
            if p.parser.verbose:
                p.parser.log('Class %s does not exist' % cname)
            if file_:
                p.parser.mofcomp.compile_file(file_, ns)
                cc = p.parser.handle.GetClass(cname, LocalOnly=False,
                                              IncludeQualifiers=True)
            else:
                if p.parser.verbose:
                    p.parser.log("Can't find file to satisfy class")
                ce = CIMError(CIM_ERR_INVALID_CLASS, cname)
                ce.file_line = (p.parser.file, p.lexer.lineno)
                raise ce
        else:
            raise
    path = CIMInstanceName(cname, namespace=ns)
    inst = CIMInstance(cname, qualifiers=quals, path=path)
    for prop in props:
        pname = prop[1]
        pval = prop[2]
        try:
            cprop = cc.properties[pname]
        except KeyError:
            ce = CIMError(CIM_ERR_INVALID_PARAMETER,
                          'Invalid property. Not in class: %s' % pname)
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce

        # confirm property name not duplicated.
        if pname in inst.properties:
            ce = CIMError(CIM_ERR_INVALID_PARAMETER,
                          'Duplicate property: %s' % pname)
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce

        try:
            # build instance property from class property but without
            # qualifiers, default value,
            pprop = cprop.copy()
            pprop.qualifiers = NocaseDict(None)
            pprop.value = tocimobj(cprop.type, pval)
            inst.properties[pname] = pprop
        except ValueError as ve:
            ce = CIMError(CIM_ERR_INVALID_PARAMETER,
                          'Invalid value for property %s: %s' %
                          (pname, str(ve)))
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce

    if alias:
        p.parser.aliases[alias] = inst.path
    p[0] = inst


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


def _find_column(input_, token):
    """
        Find the column in file where error occured. This is taken from
        token.lexpos converted to the position on the current line by
        finding the previous EOL.
    """

    i = token.lexpos
    while i > 0:
        if input_[i] == '\n':
            break
        i -= 1
    column = (token.lexpos - i) + 1
    return column


def _get_error_context(input_, token):
    """
        Build a context string that defines where on the line the defined
        error occurs.  This consists of the characters ^ at the position
        and for the length defined by the lexer position and token length
    """

    try:
        line = input_[token.lexpos: input_.index('\n', token.lexpos)]
    except ValueError:
        line = input_[token.lexpos:]

    i = input_.rfind('\n', 0, token.lexpos)
    if i < 0:
        i = 0
    line = input_[i:token.lexpos] + line
    lines = [line.strip('\r\n')]
    col = token.lexpos - i
    while len(lines) < 5 and i > 0:
        end = i
        i = input_.rfind('\n', 0, i)
        if i < 0:
            i = 0
        lines.insert(0, input_[i:end].strip('\r\n'))
    pointer = ''
    for dummy_ch in token.value:
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


@six.add_metaclass(ABCMeta)
class BaseRepositoryConnection(object):
    """
    An abstract base class for implementing repository connections for the MOF
    compiler. This class defines the interface that is used by the MOF compiler
    (class :class:`~pywbem.mof_compiler.MOFCompiler`) when it interacts with
    the repository.

    Class :class:`~pywbem.mof_compiler.MOFCompiler` invokes only the operations
    that are defined as methods on this class. Specifically, it does not
    invoke:

    * EnumerateInstances
    * GetInstance
    * EnumerateClasses
    * EnumerateClassNames
    * association or query operations
    * method invocations

    Exceptions:

      Implementation classes should raise only exceptions derived from
      :exc:`~pywbem.Error`. Other exceptions are considered programming
      errors.
    """

    # See below
    def _getns(self):
        raise NotImplementedError

    # See below
    def _setns(self, value):
        raise NotImplementedError

    # Ideally this property would be created via abstractproperty(), but then
    # Sphinx does not generate documentation for it. So we create it via
    # property() and raise NotImplementedError exceptions in the default
    # implementations of the getter/setter methods.
    default_namespace = property(
        _getns, _setns, None,
        """The default repository namespace, as a string (readable and
        writeable).""")

    @abstractmethod
    def EnumerateInstanceNames(self, *args, **kwargs):
        """Enumerate instance paths of CIM instances in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateInstanceNames`.
        """
        raise NotImplementedError

    @abstractmethod
    def CreateInstance(self, *args, **kwargs):
        """Create a CIM instance in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """
        raise NotImplementedError

    @abstractmethod
    def ModifyInstance(self, *args, **kwargs):
        """Modify a CIM instance in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.ModifyInstance`.
        """
        raise NotImplementedError

    @abstractmethod
    def DeleteInstance(self, *args, **kwargs):
        """Delete a CIM instance in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.DeleteInstance`.
        """
        raise NotImplementedError

    @abstractmethod
    def GetClass(self, *args, **kwargs):
        """Retrieve a CIM class from the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def ModifyClass(self, *args, **kwargs):
        """Modify a CIM class in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.ModifyClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def CreateClass(self, *args, **kwargs):
        """Create a CIM class in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def DeleteClass(self, *args, **kwargs):
        """Delete a CIM class in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.DeleteClass`.
        """
        raise NotImplementedError

    @abstractmethod
    def EnumerateQualifiers(self, *args, **kwargs):
        """Enumerate the qualifier types in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """
        raise NotImplementedError

    @abstractmethod
    def GetQualifier(self, *args, **kwargs):
        """Retrieve a qualifier type from the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """
        raise NotImplementedError

    @abstractmethod
    def SetQualifier(self, *args, **kwargs):
        """Create or modify a qualifier type in the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """
        raise NotImplementedError

    @abstractmethod
    def DeleteQualifier(self, *args, **kwargs):
        """Delete a qualifier type from the repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.DeleteQualifier`.
        """
        raise NotImplementedError


BaseRepositoryConnection.register(WBEMConnection)


class MOFWBEMConnection(BaseRepositoryConnection):
    """
    A repository connection that stores CIM elements locally in the
    instance of this class. It also supports removal of CIM elements
    via its :meth:`rollback` method, by rolling back the changes
    applied locally to the instance.

    It is instantiated on top of an underlying repository connection that
    is connected with the CIM repository that is actually being updated.

    This class implements the
    :class:`~pywbem.mof_compiler.BaseRepositoryConnection` interface.

    Exceptions:

      The methods of this class may raise any exceptions described for
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
        """Return either connection default or universal default namespace"""
        if self.conn is not None:
            return self.conn.default_namespace
        else:
            return self.__default_namespace

    def _setns(self, value):
        """ Set the namespace in value into either the connection default or
            package wide default namespace
        """
        if self.conn is not None:
            self.conn.default_namespace = value
        else:
            self.__default_namespace = value

    getns = _getns  # for compatibility
    setns = _setns  # for compatibility

    default_namespace = property(
        _getns, _setns, None,
        """The default repository namespace, as a string (readable and
        writeable).""")

    def EnumerateInstanceNames(self, *args, **kwargs):
        """This method is used by the MOF compiler only when it creates a
        namespace in the course of handling CIM_ERR_NAMESPACE_NOT_FOUND.
        Because the operations of this class silently create every namespace
        that is needed and never return that error, this method is never
        called, and is therefore not implemented.
        """

        raise CIMError(CIM_ERR_FAILED, 'This should not happen!')

    def ModifyInstance(self, *args, **kwargs):
        """This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to create an instance.
        Because :meth:`CreateInstance` overwrites existing instances, this
        method is never called, and is therefore not implemented.
        """

        raise CIMError(CIM_ERR_FAILED, 'This should not happen!')

    def CreateInstance(self, *args, **kwargs):
        """Create a CIM instance in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """

        inst = len(args) > 0 and args[0] or kwargs['NewInstance']
        try:
            self.instances[self.default_namespace].append(inst)
        except KeyError:
            self.instances[self.default_namespace] = [inst]
        return inst.path

    def DeleteInstance(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(CIM_ERR_FAILED, 'This should not happen!')

    def GetClass(self, *args, **kwargs):
        """Retrieve a CIM class from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """

        cname = len(args) > 0 and args[0] or kwargs['ClassName']
        try:
            cc = self.classes[self.default_namespace][cname]
        except KeyError:
            if self.conn is None:
                ce = CIMError(CIM_ERR_NOT_FOUND, cname)
                raise ce
            cc = self.conn.GetClass(*args, **kwargs)
            try:
                self.classes[self.default_namespace][cc.classname] = cc
            except KeyError:
                self.classes[self.default_namespace] = \
                    NocaseDict({cc.classname: cc})
        if 'LocalOnly' in kwargs and not kwargs['LocalOnly']:
            if cc.superclass:
                try:
                    del kwargs['ClassName']
                except KeyError:
                    pass
                if len(args) > 0:
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

        raise CIMError(CIM_ERR_FAILED, 'This should not happen!')

    def CreateClass(self, *args, **kwargs):
        """Create a CIM class in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateClass`.
        """

        cc = len(args) > 0 and args[0] or kwargs['NewClass']
        # TODO 2016/03 AM: Dubious stmt above.
        if cc.superclass:
            try:
                _ = self.GetClass(cc.superclass, LocalOnly=True,  # noqa: F841
                                  IncludeQualifiers=False)
            except CIMError as ce:
                if ce.args[0] == CIM_ERR_NOT_FOUND:
                    ce.args = (CIM_ERR_INVALID_SUPERCLASS, cc.superclass)
                    raise
                else:
                    raise

        try:
            self.compile_ordered_classnames.append(cc.classname)

            # The following generates an exception for each new ns
            self.classes[self.default_namespace][cc.classname] = cc
        except KeyError:
            self.classes[self.default_namespace] = \
                NocaseDict({cc.classname: cc})

        # TODO: should we see if it exists first with
        # self.conn.GetClass()?  Do we want to create a class
        # that already existed?
        try:
            self.class_names[self.default_namespace].append(cc.classname)
        except KeyError:
            self.class_names[self.default_namespace] = [cc.classname]

    def DeleteClass(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(CIM_ERR_FAILED, 'This should not happen!')

    def EnumerateQualifiers(self, *args, **kwargs):
        """Enumerate the qualifier types in the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.
        """

        if self.conn is not None:
            rv = self.conn.EnumerateQualifiers(*args, **kwargs)
        else:
            rv = []
        try:
            rv += list(self.qualifiers[self.default_namespace].values())
        except KeyError:
            pass
        return rv

    def GetQualifier(self, *args, **kwargs):
        """Retrieve a qualifier type from the local repository of this class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetQualifier`.
        """

        qualname = len(args) > 0 and args[0] or kwargs['QualifierName']
        try:
            qual = self.qualifiers[self.default_namespace][qualname]
        except KeyError:
            if self.conn is None:
                raise CIMError(CIM_ERR_NOT_FOUND, qualname)
            qual = self.conn.GetQualifier(*args, **kwargs)
        return qual

    def SetQualifier(self, *args, **kwargs):
        """Create or modify a qualifier type in the local repository of this
        class.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.SetQualifier`.
        """

        qual = len(args) > 0 and args[0] or kwargs['QualifierDeclaration']
        try:
            self.qualifiers[self.default_namespace][qual.name] = qual
        except KeyError:
            self.qualifiers[self.default_namespace] = \
                NocaseDict({qual.name: qual})

    def DeleteQualifier(self, *args, **kwargs):
        """This method is only invoked by :meth:`rollback` (on the underlying
        repository), and never by the MOF compiler, and is therefore not
        implemented."""

        raise CIMError(CIM_ERR_FAILED, 'This should not happen!')

    def rollback(self, verbose=False):
        """
        Remove classes and instances from the underlying repository, that have
        been created in the local repository of this class.

        Limitation: At this point, only classes and instances will be removed,
        but not qualifiers.
        """
        for ns, insts in self.instances.items():
            insts.reverse()
            for inst in insts:
                try:
                    if verbose:
                        print('Deleting instance %s' % inst.path)
                    self.conn.DeleteInstance(inst.path)
                except CIMError as ce:
                    print('Error deleting instance %s' % inst.path)
                    print('     %s %s' % (ce.args[0], ce.args[1]))
        for ns, cnames in self.class_names.items():
            self.default_namespace = ns
            cnames.reverse()
            for cname in cnames:
                try:
                    if verbose:
                        print('Deleting class %s:%s' % (ns, cname))
                    self.conn.DeleteClass(cname)
                except CIMError as ce:
                    print('Error deleting class %s:%s' % (ns, cname))
                    print('     %s %s' % (ce.args[0], ce.args[1]))
        # TODO: We want rollback to do something with qualifiers?


def _print_logger(msg):
    """Print the `msg` parameter to stdout."""
    print(msg)


class MOFCompiler(object):
    """
    A MOF compiler.

    A MOF compiler is associated with a CIM repository. The repository is
    used for looking up dependent CIM elements (e.g. the superclass specified
    in a class whose MOF definition is being compiled), and it is also updated
    with the result of the compilation. A repository contains CIM namespaces,
    and the namespaces contain CIM classes, instances and qualifier types.

    The association with a CIM repository is established when creating an
    instance of this class. The interactions with the CIM repository are
    defined in the abstract base class
    :class:`~pywbem.mof_compiler.BaseRepositoryConnection`.
    """

    def __init__(self, handle, search_paths=None, verbose=False,
                 log_func=_print_logger):
        """
        Parameters:

          handle (BaseRepositoryConnection):
            A connection to the CIM repository that will be associated with the
            MOF compiler.

            `None` means that no CIM repository will be associated. In this
            case, the MOF compiler can only process standalone MOF that does
            not depend on existing CIM elements in the repository.

          search_paths (:term:`py:iterable` of :term:`string`):
            An iterable of path names of directories where MOF include files
            should be looked up.

          verbose (:class:`py:bool`):
            Indicates whether to issue more detailed compiler messages.

          log_func (:term:`callable`):
            A logger function that is invoked for each compiler message.
            The logger function must take one parameter of string type.
            The default logger prints to stdout.
        """

        self.parser = _yacc(verbose)
        self.parser.search_paths = search_paths if search_paths else []
        self.handle = handle
        self.parser.handle = handle
        self.lexer = _lex(verbose)
        self.lexer.parser = self.parser
        self.parser.qualcache = {}
        self.parser.classnames = {}
        if handle:
            default_namespace = handle.default_namespace
            self.parser.qualcache[default_namespace] = NocaseDict()
            self.parser.classnames[default_namespace] = []
        self.parser.mofcomp = self
        self.parser.verbose = verbose
        self.parser.log = log_func
        self.parser.aliases = {}

    def compile_string(self, mof, ns, filename=None):
        """
        Compile a string of MOF statements into a namespace of the associated
        CIM repository.

        Parameters:

          mof (:term:`string`):
            The string of MOF statements to be compiled.

          ns (:term:`string`):
            The name of the CIM namespace in the associated CIM repository
            that is used for lookup of any dependent CIM elements, and that
            is also the target of the compilation.

          filename (:term:`string`):
            The path name of the file that the MOF statements were read from.
            This information is used only in compiler messages.

        Raises:

          MOFParseError: Syntax error in the MOF.

          : Any exceptions that are raised by the repository connection class.
        """

        lexer = self.lexer.clone()
        lexer.parser = self.parser
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
        self.parser.handle.default_namespace = ns
        if ns not in self.parser.qualcache:
            self.parser.qualcache[ns] = NocaseDict()
        if ns not in self.parser.classnames:
            self.parser.classnames[ns] = []
        try:
            # Call the parser.  To generate detailed output of states
            # add debug=1 to following line.
            rv = self.parser.parse(mof, lexer=lexer)
            self.parser.file = oldfile
            self.parser.mof = oldmof
            return rv

        except MOFParseError as pe:
            # Generate the error message into log and reraise error
            self.parser.log(pe.get_err_msg())
            raise

        except CIMError as ce:
            if hasattr(ce, 'file_line'):
                self.parser.log('Fatal Error: %s:%s' % (ce.file_line[0],
                                                        ce.file_line[1]))
            else:
                self.parser.log('Fatal Error:')

            self.parser.log('%s%s' % (_statuscode2string(ce.args[0]),
                                      ce.args[1] and ': ' + ce.args[1] or ''))
            raise

    def compile_file(self, filename, ns):
        """
        Compile a MOF file into a namespace of the associated CIM repository.

        Parameters:

          filename (:term:`string`):
            The path name of the MOF file containing the MOF statements to be
            compiled.

          ns (:term:`string`):
            The name of the CIM namespace in the associated CIM repository
            that is used for lookup of any dependent CIM elements, and that
            is also the target of the compilation.

        Raises:

          MOFParseError: Syntax error in the MOF.

          : Any exceptions that are raised by the repository connection class.
        """

        if self.parser.verbose:
            self.parser.log('Compiling file ' + filename)

        f = open(filename, 'r')
        mof = f.read()
        f.close()

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

          A string with the path name of the MOF file, if it was found.
          `None`, otherwise.
        """

        classname = classname.lower()
        for search in self.parser.search_paths:
            for root, dummy_dirs, files in os.walk(search):
                for file_ in files:
                    if file_.endswith('.mof') and \
                            file_[:-4].lower() == classname:
                        return root + '/' + file_
        return None

    def rollback(self, verbose=False):
        """
        Rollback any changes to the CIM repository that were performed by
        compilations using this MOF compiler object, since the object was
        created.
        """

        self.handle.rollback(verbose=verbose)


def _build(verbose=False):
    """Build the LEX and YACC table modules for the MOF compiler, if they do
    not exist yet, or if their table versions do not match the installed
    version of the `ply` package.
    """

    if verbose:
        print("Building LEX/YACC modules for MOF compiler in: %s" % _tabdir)

    _yacc(verbose)
    _lex(verbose)


def _yacc(verbose=False):
    """Return YACC parser object for the MOF compiler.

    As a side effect, the YACC table module for the MOF compiler gets created
    if it does not exist yet, or updated if its table version does not match
    the installed version of the `ply` package.
    """

    # In yacc(), the 'debug' parameter controls the main error
    # messages to the 'errorlog' in addition to the debug messages
    # to the 'debuglog'. Because we want to see the error messages,
    # we enable debug but set the debuglog to the NullLogger.
    return yacc.yacc(optimize=_optimize,
                     tabmodule=_tabmodule,
                     outputdir=_tabdir,
                     debug=True,
                     debuglog=yacc.NullLogger(),
                     errorlog=yacc.PlyLogger(sys.stdout))


def _lex(verbose=False):
    """Return LEX analyzer object for the MOF Compiler.

    As a side effect, the LEX table module for the MOF compiler gets created
    if it does not exist yet, or updated if its table version does not match
    the installed version of the `ply` package.
    """

    return lex.lex(optimize=_optimize,
                   lextab=_lextab,
                   outputdir=_tabdir,
                   debug=False,
                   errorlog=lex.PlyLogger(sys.stdout))
