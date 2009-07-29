#!/usr/bin/env python
#
# (C) Copyright 2006-2007 Novell, Inc. 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
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

import sys
import os
import lex
import yacc
from lex import TOKEN
from cim_operations import CIMError, WBEMConnection
from cim_obj import *
from cim_constants import *
from getpass import getpass

_optimize = 1
_tabmodule='mofparsetab'
_lextab='moflextab'


reserved = {
    'any':'ANY',
    'as':'AS',
    'association':'ASSOCIATION',
    'class':'CLASS',
    'disableoverride':'DISABLEOVERRIDE',
    'boolean':'DT_BOOL',
    'char16':'DT_CHAR16',
    'datetime':'DT_DATETIME',
    'pragma':'PRAGMA',
    'real32':'DT_REAL32',
    'real64':'DT_REAL64',
    'sint16':'DT_SINT16',
    'sint32':'DT_SINT32',
    'sint64':'DT_SINT64',
    'sint8':'DT_SINT8',
    'string':'DT_STR',
    'uint16':'DT_UINT16',
    'uint32':'DT_UINT32',
    'uint64':'DT_UINT64',
    'uint8':'DT_UINT8',
    'enableoverride':'ENABLEOVERRIDE',
    'false':'FALSE',
    'flavor':'FLAVOR',
    'indication':'INDICATION',
    'instance':'INSTANCE',
    'method':'METHOD',
    'null':'NULL',
    'of':'OF',
    'parameter':'PARAMETER',
    'property':'PROPERTY',
    'qualifier':'QUALIFIER',
    'ref':'REF',
    'reference':'REFERENCE',
    'restricted':'RESTRICTED',
    'schema':'SCHEMA',
    'scope':'SCOPE',
    'tosubclass':'TOSUBCLASS',
    'translatable':'TRANSLATABLE',
    'true':'TRUE',
    }

tokens = reserved.values() + [
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

utf8Char = r'(%s)|(%s)|(%s)|(%s)|(%s)|(%s)|(%s)|(%s)' % (utf8_2, utf8_3_1,
        utf8_3_2, utf8_3_3, utf8_3_4, utf8_4_1, utf8_4_2, utf8_4_3)

def t_COMMENT(t):
    r'//.*'
    pass

def t_MCOMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lineno += t.value.count('\n')


t_binaryValue = r'[+-]?[01]+[bB]'
t_octalValue = r'[+-]?0[0-7]+'
t_decimalValue = r'[+-]?([1-9][0-9]*|0)'
t_hexValue = r'[+-]?0[xX][0-9a-fA-F]+'
t_floatValue = r'[+-]?[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?'

simpleEscape = r"""[bfnrt'"\\]"""
hexEscape = r'x[0-9a-fA-F]{1,4}'
escapeSequence = r'[\\]((%s)|(%s))' % (simpleEscape, hexEscape)
cChar = r"[^'\\\n\r]|(%s)" % escapeSequence
sChar = r'[^"\\\n\r]|(%s)' % escapeSequence
charValue = r"'%s'" % cChar

t_stringValue = r'"(%s)*"' % sChar

identifier_re = r'([a-zA-Z_]|(%s))([0-9a-zA-Z_]|(%s))*' % (utf8Char, utf8Char)

@TOKEN(identifier_re)
def t_IDENTIFIER(t):
    t.type = reserved.get(t.value.lower(),'IDENTIFIER') # check for reserved word
    return t

# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.linestart = t.lexpos

t_ignore = ' \r\t'

# Error handling rule
def t_error(t):
    msg = "Illegal character '%s' " % t.value[0]
    msg+= "Line %d, col %d" % (t.lineno, _find_column(t.lexer.parser.mof, t))
    t.lexer.parser.log(msg)
    t.lexer.skip(1)

class MOFParseError(ValueError):
    pass

def p_error(p):
    ex = MOFParseError()
    if p is None:
        ex.args = ('Unexpected end of file',)
        raise ex
    ex.file = p.lexer.parser.file
    ex.lineno = p.lineno
    ex.column = _find_column(p.lexer.parser.mof, p)
    ex.context = _get_error_context(p.lexer.parser.mof, p)
    raise ex


def p_mofSpecification(p):
    """mofSpecification : mofProductionList"""

def p_mofProductionList(p):
    """mofProductionList : empty
                         | mofProductionList mofProduction
                           """

def p_mofProduction(p):
    """mofProduction : compilerDirective
                     | mp_createClass
                     | mp_setQualifier
                     | mp_createInstance
                     """


def _create_ns(p, handle, ns):
    # Figure out the flavor of cim server
    cimom_type = None
    ns = ns.strip('/')
    try:
        inames = handle.EnumerateInstanceNames('__Namespace', namespace='root')
        inames = [x['name'] for x in inames]
        if 'PG_InterOp' in inames:
            cimom_type = 'pegasus'
    except CIMError, ce:
        if ce.args[0] != CIM_ERR_NOT_FOUND:
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise
    if not cimom_type:
        try:
            inames = handle.EnumerateInstanceNames('CIM_Namespace', 
                    namespace='Interop')
            inames = [x['name'] for x in inames]
            cimom_type = 'proper'
        except CIMError, ce:
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
        inst = CIMInstance('__Namespace', 
                properties={'Name':''},
                path=CIMInstanceName('__Namespace', 
                    keybindings={'Name':''},
                    namespace=ns))
        try:
            handle.CreateInstance(inst)
        except CIMError, ce:
            if ce.args[0] != CIM_ERR_ALREADY_EXISTS:
                ce.file_line = (p.parser.file, p.lexer.lineno)
                raise

    elif cimom_type == 'proper':
        inst = CIMInstance('CIM_Namespace', 
                properties={'Name': ns},
                path=CIMInstanceName('CIM_Namespace',
                    namespace='root',
                    keybindings={'Name':ns}))
        handle.CreateInstance(inst)




def p_mp_createClass(p):
    """mp_createClass : classDeclaration
                      | assocDeclaration
                      | indicDeclaration
                      """
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
                    p.parser.log('Created class %s:%s' % (ns,cc.classname))
                p.parser.classnames[ns].append(cc.classname.lower())
                break
            except CIMError, ce:
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
                                p.parser.mofcomp.compile_file(qualfile,ns)
                    if not p.parser.qualcache[ns]:
                        # can't find qualifiers
                        raise
                    objects = cc.properties.values()
                    for meth in cc.methods.values():
                        objects+= meth.parameters.values()
                    dep_classes = []
                    for obj in objects:
                        if obj.type not in ['reference','string']:
                            continue
                        if obj.type == 'reference':
                            if obj.reference_class.lower() not in dep_classes:
                                dep_classes.append(obj.reference_class.lower())
                            continue
                        # else obj.type is 'string'
                        try:
                            embedded_inst= obj.qualifiers['embeddedinstance']
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
    
    except CIMError, ce:
        ce.file_line = (p.parser.file, p.lexer.lineno)
        if ce.args[0] != CIM_ERR_ALREADY_EXISTS:
            raise
        if p.parser.verbose:
            p.parser.log('Class %s already exist.  Modifying...' % cc.classname)
        try:
            p.parser.handle.ModifyClass(cc, ns)
        except CIMError, ce:
            p.parser.log('Error Modifying class %s: %s, %s' 
                    % (cc.classname, ce.args[0], ce.args[1]))

def p_mp_createInstance(p):
    """mp_createInstance : instanceDeclaration"""
    inst = p[1]
    if p.parser.verbose:
        p.parser.log('Creating instance of %s.' % inst.classname)
    try:
        p.parser.handle.CreateInstance(inst)
    except CIMError, ce:
        if ce.args[0] == CIM_ERR_ALREADY_EXISTS:
            if p.parser.verbose:
                p.parser.log('Instance of class %s already exist.  Modifying...'  % inst.classname)
            try:
                p.parser.handle.ModifyInstance(inst)
            except CIMError, ce:
                if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                    if p.parser.verbose:
                        p.parser.log('ModifyInstance not supported.  Deleting instance of %s: %s' % (inst.classname, inst.path))
                    p.parser.handle.DeleteInstance(inst.path)
                    if p.parser.verbose:
                        p.parser.log('Creating instance of %s.' % inst.classname)
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
    except CIMError, ce:
        if ce.args[0] == CIM_ERR_INVALID_NAMESPACE:
            if p.parser.verbose:
                p.parser.log('Creating namespace ' + ns)
            _create_ns(p, p.parser.handle, ns)
            if p.parser.verbose:
                p.parser.log('Setting qualifier %s' % qualdecl.name)
            p.parser.handle.SetQualifier(qualdecl)
        elif ce.args[0] == CIM_ERR_NOT_SUPPORTED:
            if p.parser.verbose:
                p.parser.log('Qualifier %s already exists.  Deleting...' 
                            % qualdecl.name)
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
        #if p.parser.file:
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
    """classDeclaration : CLASS className '{' classFeatureList '}' ';'
                        | CLASS className superClass '{' classFeatureList '}' ';'
                        | CLASS className alias '{' classFeatureList '}' ';'
                        | CLASS className alias superClass '{' classFeatureList '}' ';'
                        | qualifierList CLASS className '{' classFeatureList '}' ';'
                        | qualifierList CLASS className superClass '{' classFeatureList '}' ';'
                        | qualifierList CLASS className alias '{' classFeatureList '}' ';'
                        | qualifierList CLASS className alias superClass '{' classFeatureList '}' ';'
                        """
    superclass = None
    alias = None
    quals = []
    if isinstance(p[1], basestring): # no class qualifiers
        cname = p[2]
        if p[3][0] == '$': # alias present
            alias = p[3]
            if p[4] == '{': # no superclass
                cfl = p[5]
            else: # superclass
                superclass = p[4]
                cfl = p[6]
        else: # no alias
            if p[3] == '{': # no superclass
                cfl = p[4]
            else: # superclass
                superclass = p[3]
                cfl = p[5]
    else: # class qualifiers
        quals = p[1]
        cname = p[3]
        if p[4][0] == '$': # alias present
            alias = p[4]
            if p[5] == '{': # no superclass
                cfl = p[6]
            else: # superclass
                superclass = p[5]
                cfl = p[7]
        else: # no alias
            if p[4] == '{': # no superclass
                cfl = p[5]
            else: # superclass
                superclass = p[4]
                cfl = p[6]
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
    """assocDeclaration : '[' ASSOCIATION qualifierListEmpty ']' CLASS className '{' associationFeatureList '}' ';'
                        | '[' ASSOCIATION qualifierListEmpty ']' CLASS className superClass '{' associationFeatureList '}' ';'
                        | '[' ASSOCIATION qualifierListEmpty ']' CLASS className alias '{' associationFeatureList '}' ';'
                        | '[' ASSOCIATION qualifierListEmpty ']' CLASS className alias superClass '{' associationFeatureList '}' ';'
                        """
    aqual = CIMQualifier('ASSOCIATION', True, type='boolean')
    # TODO flavor trash. 
    quals = [aqual] + p[3]
    p[0] = _assoc_or_indic_decl(quals, p)
    
def p_indicDeclaration(p):
    """indicDeclaration : '[' INDICATION qualifierListEmpty ']' CLASS className '{' classFeatureList '}' ';'
                        | '[' INDICATION qualifierListEmpty ']' CLASS className superClass '{' classFeatureList '}' ';'
                        | '[' INDICATION qualifierListEmpty ']' CLASS className alias '{' classFeatureList '}' ';'
                        | '[' INDICATION qualifierListEmpty ']' CLASS className alias superClass '{' classFeatureList '}' ';'
                        """
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
    elif p[7][0] == '$': # alias
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
        except CIMError, ce:
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
        
    flavors = _build_flavors(flavorlist, qualdecl)
    if qval is None: 
        if qualdecl.type == 'boolean':
            qval = True
        else:
            qval = qualdecl.value # default value
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

def p_flavor(p):
    """flavor : ENABLEOVERRIDE
              | DISABLEOVERRIDE
              | RESTRICTED
              | TOSUBCLASS
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
    """propertyDeclaration_6 : qualifierList dataType propertyName defaultValue ';'"""
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], tocimobj(p[2], p[4]), 
            type=p[2], qualifiers=quals)

def p_propertyDeclaration_7(p):
    """propertyDeclaration_7 : qualifierList dataType propertyName array ';'"""
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], None, type=p[2], qualifiers=quals,
            is_array=True, array_size=p[4])

def p_propertyDeclaration_8(p):
    """propertyDeclaration_8 : qualifierList dataType propertyName array defaultValue ';'"""
    quals = dict([(x.name, x) for x in p[1]])
    p[0] = CIMProperty(p[3], tocimobj(p[2], p[5]), 
            type=p[2], qualifiers=quals, is_array=True, array_size=p[4])

def p_referenceDeclaration(p):
    """referenceDeclaration : objectRef referenceName ';'
                            | objectRef referenceName defaultValue ';'
                            | qualifierList objectRef referenceName ';'
                            | qualifierList objectRef referenceName defaultValue ';'
                            """
    quals = []
    dv = None
    if isinstance(p[1], list): # qualifiers
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
    quals = dict([(x.name, x) for x in quals])
    p[0] = CIMProperty(pname, dv, type='reference', 
            reference_class=cname, qualifiers=quals)

def p_methodDeclaration(p):
    """methodDeclaration : dataType methodName '(' ')' ';'
                         | dataType methodName '(' parameterList ')' ';'
                         | qualifierList dataType methodName '(' ')' ';'
                         | qualifierList dataType methodName '(' parameterList ')' ';'
                         """
    paramlist = []
    quals = []
    if isinstance(p[1], basestring): # no quals
        dt = p[1]
        mname = p[2]
        if p[4] != ')':
            paramlist = p[4]
    else: # quals present
        quals = p[1]
        dt = p[2]
        mname = p[3]
        if p[5] != ')':
            paramlist = p[5]
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
    s = s[1:-1]
    rv = ''
    esc = False
    i = -1 
    while i < len(s) -1:
        i+= 1
        ch = s[i]
        if ch == '\\' and not esc:
            esc = True
            continue
        if not esc:
            rv+= ch
            continue

        if ch == '"'   : rv+= '"'
        elif ch == 'n' : rv+= '\n'
        elif ch == 't' : rv+= '\t'
        elif ch == 'b' : rv+= '\b'
        elif ch == 'f' : rv+= '\f'
        elif ch == 'r' : rv+= '\r'
        elif ch == '\\': rv+= '\\'
        elif ch in ['x','X']:
            hexc = 0
            j = 0
            i+= 1
            while j < 4:
                c = s[i+j]; 
                c = c.upper()
                if not c.isdigit() and not c in 'ABCDEF':
                    break;
                hexc <<= 4
                if c.isdigit():
                    hexc |= ord(c) - ord('0')
                else:
                    hexc |= ord(c) - ord('A') + 0XA
                j+= 1
            rv+= chr(hexc)
            i+= j-1

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
                    'Unknown alias: ' + p[0])
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce
    else:
        p[0] = p[1]

def p_objectHandle(p):
    """objectHandle : identifier"""
    p[0] = p[1]

def p_qualifierDeclaration(p):
    """qualifierDeclaration : QUALIFIER qualifierName qualifierType scope ';'
                            | QUALIFIER qualifierName qualifierType scope defaultFlavor ';'
                            """
    qualtype = p[3]
    dt, is_array, array_size, value = qualtype
    qualname = p[2]
    scopes = p[4]
    if len(p) == 5:
        flist = []
    else:
        flist = p[5]
    flavors = _build_flavors(flist)

    p[0] = CIMQualifierDeclaration(qualname, dt, value=value, 
                    is_array=is_array, array_size=array_size, 
                    scopes=scopes, **flavors)

def _build_flavors(flist, qualdecl=None):
    flavors = {}
    if qualdecl is not None:
        flavors = {'overridable':qualdecl.overridable,
                   'translatable':qualdecl.translatable,
                   'toinstance':qualdecl.toinstance,
                   'tosubclass':qualdecl.tosubclass}
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
    try:
        if flavors['tosubclass']:
            flavors['toinstance'] = True
    except KeyError:
        pass
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
    for i in ('SCHEMA',
              'CLASS',
              'ASSOCIATION',
              'INDICATION',
              'QUALIFIER',
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
    flavors = {'ENABLEOVERRIDE':True,
               'TOSUBCLASS':True,
               'DISABLEOVERRIDE':False,
               'RESTRICTED':False,
               'TRANSLATABLE':False}
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
    """instanceDeclaration : INSTANCE OF className '{' valueInitializerList '}' ';'
                           | INSTANCE OF className alias '{' valueInitializerList '}' ';'
                           | qualifierList INSTANCE OF className '{' valueInitializerList '}' ';'
                           | qualifierList INSTANCE OF className alias '{' valueInitializerList '}' ';'
                           """
    alias = None
    quals = {}
    ns = p.parser.handle.default_namespace
    if isinstance(p[1], basestring): # no qualifiers
        cname = p[3]
        if p[4] == '{':
            props = p[5]
        else:
            props = p[6]
            alias = p[4]
    else:
        cname = p[4]
        #quals = p[1] # qualifiers on instances are deprecated -- rightly so. 
        if p[5] == '{':
            props = p[6]
        else:
            props = p[7]
            alias = p[5]

    try:
        cc = p.parser.handle.GetClass(cname,
                LocalOnly=False, IncludeQualifiers=True)
        p.parser.classnames[ns].append(cc.classname.lower())
    except CIMError, ce:
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
    inst = CIMInstance(cname, properties=cc.properties, 
            qualifiers=quals, path=path)
    for prop in props: 
        pname = prop[1]
        pval = prop[2]
        try:
            cprop = inst.properties[pname]
            cprop.value = tocimobj(cprop.type, pval)
        except KeyError:
            ce = CIMError(CIM_ERR_INVALID_PARAMETER, 
                    'Invalid property: %s' % pname)
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce
        except ValueError, ve:
            ce = CIMError(CIM_ERR_INVALID_PARAMETER, 
                    'Invalid value for property: %s: %s' % (pname,ve.message))
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce

    for prop in inst.properties.values():
        if 'key' not in prop.qualifiers or not prop.qualifiers['key']:
            continue
        if prop.value is None: 
            ce = CIMError(CIM_ERR_FAILED, 
                    'Key property %s.%s is not set' % (cname, prop.name))
            ce.file_line = (p.parser.file, p.lexer.lineno)
            raise ce
        inst.path.keybindings[prop.name] = prop.value

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
                  | TRANSLATABLE
                  """
                  #| ASSOCIATION
                  #| INDICATION
    p[0] = p[1]

def p_empty(p):
    'empty :'
    pass

def _find_column(input, token):
    i = token.lexpos
    while i > 0:
        if input[i] == '\n':
            break
        i-= 1
    column = (token.lexpos - i)+1
    return column

def _get_error_context(input, token):
    try:
        line = input[token.lexpos : input.index('\n', token.lexpos)]
    except ValueError:
        line = input[token.lexpos:]
    i = input.rfind('\n', 0, token.lexpos)
    if i < 0: 
        i = 0
    line = input[i:token.lexpos] + line
    lines = [line.strip('\r\n')]
    col = token.lexpos - i
    while len(lines) < 5 and i > 0:
        end = i
        i = input.rfind('\n', 0, i)
        if i < 0:
            i = 0
        lines.insert(0, input[i:end].strip('\r\n'))
    pointer = ''
    for ch in token.value:
        pointer+= '^'
    pointline = ''
    i = 0
    while i < col -1:
        if lines[-1][i].isspace():
            pointline+= lines[-1][i]
            # otherwise, tabs complicate the alignment
        else:
            pointline+= ' '
        i+= 1
    lines.append(pointline + pointer)
    return lines

def _print_logger(str):
    print str


class MOFWBEMConnection(object):
    def __init__(self, conn=None):
        self.conn = conn
        self.class_names = {}
        self.qualifiers = {}
        self.instances = {}
        self.classes = {}
        if conn is None:
            self.__default_namespace = 'root/cimv2'

    def setns(self, value):
        if self.conn is not None:
            self.conn.default_namespace = value
        else:
            self.__default_namespace = value

    def getns(self):
        if self.conn is not None:
            return self.conn.default_namespace
        else:
            return self.__default_namespace

    default_namespace = property(getns, setns, None, 
            "default_namespace property")

    def GetClass(self, *args, **kwargs):
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
                        NocaseDict({cc.classname:cc})
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

    def CreateClass(self, *args, **kwargs):
        cc = len(args) > 0 and args[0] or kwargs['NewClass']
        if cc.superclass:
            try:
                super_ = self.GetClass(cc.superclass, LocalOnly=True, 
                        IncludeQualifiers=False)
            except CIMError, ce:
                if ce.args[0] == CIM_ERR_NOT_FOUND:
                    ce.args = (CIM_ERR_INVALID_SUPERCLASS, cc.superclass)
                    raise
                else:
                    raise

        try:
            self.classes[self.default_namespace][cc.classname] = cc
        except KeyError:
            self.classes[self.default_namespace] = \
                        NocaseDict({cc.classname:cc})

        # TODO: should we see if it exists first with 
        # self.conn.GetClass()?  Do we want to create a class
        # that already existed? 
        try:
            self.class_names[self.default_namespace].append(cc.classname)
        except KeyError:
            self.class_names[self.default_namespace] = [cc.classname]

    def ModifyClass(self, *args, **kwargs):
        raise CIMError(CIM_ERR_FAILED, 
                'This should not happen!')

    def ModifyInstance(self, *args, **kwargs):
        raise CIMError(CIM_ERR_FAILED, 
                'This should not happen!')

    def GetQualifier(self, *args, **kwargs):
        qualname = len(args) > 0 and args[0] or kwargs['QualifierName']
        try:
            qual = self.qualifiers[self.default_namespace][qualname]
        except KeyError:
            if self.conn is None:
                raise CIMError(CIM_ERR_NOT_FOUND, qualname)
            qual = self.conn.GetQualifier(*args, **kwargs)
        return qual

    def SetQualifier(self, *args, **kwargs):
        qual = len(args) > 0 and args[0] or kwargs['QualifierDeclaration']
        try:
            self.qualifiers[self.default_namespace][qual.name] = qual
        except KeyError:
            self.qualifiers[self.default_namespace] = \
                    NocaseDict({qual.name:qual})

    def EnumerateQualifiers(self, *args, **kwargs):
        if self.conn is not None:
            rv = self.conn.EnumerateQualifiers(*args, 
                    **kwargs)
        else:
            rv = []
        try:
            rv+= self.qualifiers[self.default_namespace].values()
        except KeyError:
            pass
        return rv


    def CreateInstance(self, *args, **kwargs):
        inst = len(args) > 0 and args[0] or kwargs['NewInstance']
        try:
            self.instances[self.default_namespace].append(inst)
        except KeyError:
            self.instances[self.default_namespace] = [inst]
        return inst.path

    def rollback(self, verbose=False):
        for ns, insts in self.instances.items():
            insts.reverse()
            for inst in insts:
                try:
                    if verbose:
                        print 'Deleting instance', inst.path
                    self.conn.DeleteInstance(inst.path)
                except CIMError, ce:
                    print 'Error deleting instance', inst.path
                    print '    ', '%s %s' % (ce.args[0], ce.args[1])
        for ns, cnames in self.class_names.items():
            self.default_namespace = ns
            cnames.reverse()
            for cname in cnames:
                try:
                    if verbose:
                        print 'Deleting class %s:%s' % (ns, cname)
                    self.conn.DeleteClass(cname)
                except CIMError, ce:
                    print 'Error deleting class %s:%s' % (ns, cname)
                    print '    ', '%s %s' % (ce.args[0], ce.args[1])
        # TODO: do we want to do anything with qualifiers? 


def _errcode2string(code):
    d = {
        CIM_ERR_FAILED                 : 'A general error occurred',
        CIM_ERR_ACCESS_DENIED          : 'Resource not available',
        CIM_ERR_INVALID_NAMESPACE      : 'The target namespace does not exist',
        CIM_ERR_INVALID_PARAMETER      : 'Parameter value(s) invalid',
        CIM_ERR_INVALID_CLASS          : 'The specified Class does not exist',
        CIM_ERR_NOT_FOUND              : 'Requested object could not be found',
        CIM_ERR_NOT_SUPPORTED          : 'Operation not supported',
        CIM_ERR_CLASS_HAS_CHILDREN     : 'Class has subclasses',
        CIM_ERR_CLASS_HAS_INSTANCES    : 'Class has instances',
        CIM_ERR_INVALID_SUPERCLASS     : 'Superclass does not exist',
        CIM_ERR_ALREADY_EXISTS         : 'Object already exists',
        CIM_ERR_NO_SUCH_PROPERTY       : 'Property does not exist',
        CIM_ERR_TYPE_MISMATCH          : 'Value incompatible with type',
        CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED   : 'Query language not supported',
        CIM_ERR_INVALID_QUERY          : 'Query not valid',
        CIM_ERR_METHOD_NOT_AVAILABLE   : 'Extrinsic method not executed',
        CIM_ERR_METHOD_NOT_FOUND       : 'Extrinsic method does not exist',
        }
    try:
        s = d[code]
    except KeyError:
        s = 'Unknown Error'
    return s

class MOFCompiler(object):
    def __init__(self, handle, search_paths=[], verbose=False,
                 log_func=_print_logger):
        """Initialize the compiler.

        Keyword arguments:
        handle -- A WBEMConnection or similar object.  The following 
            attributes and methods need to be present, corresponding to the 
            the attributes and methods on pywbem.WBEMConnection having 
            the same names:
            - default_namespace
            - EnumerateInstanceNames()
            - CreateClass()
            - GetClass()
            - ModifyClass()
            - DeleteInstance()
            - CreateInstance()
            - ModifyInstance()
            - DeleteQualifier()
            - EnumerateQualifiers()
            - SetQualifier()
        search_paths -- A list of file system paths specifying where 
            missing schema elements should be looked for. 
        verbose -- True if extra messages should be printed. 
        log_func -- A callable that takes a single string argument.  
            The default logger prints to stdout. 
        """

        self.parser = yacc.yacc(tabmodule=_tabmodule, optimize=_optimize)
        self.parser.search_paths = search_paths
        self.handle = handle
        self.parser.handle = handle
        self.lexer = lex.lex(lextab=_lextab, optimize=_optimize)
        self.lexer.parser = self.parser
        self.parser.qualcache = {handle.default_namespace:NocaseDict()}
        self.parser.classnames = {handle.default_namespace:[]}
        self.parser.mofcomp = self
        self.parser.verbose = verbose
        self.parser.log = log_func
        self.parser.aliases = {}

    def compile_string(self, mof, ns, filename=None):
        """Compile a string of MOF.

        Arguments:
        mof -- The string of MOF
        ns -- The CIM namespace

        Keyword arguments:
        filename -- The name of the file that the MOF was read from.  This 
            is used in status and error messages.
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
            rv = self.parser.parse(mof, lexer=lexer)
            self.parser.file = oldfile
            self.parser.mof = oldmof
            return rv
        except MOFParseError, pe:
            self.parser.log('Syntax error:')
            if hasattr(pe, 'file') and hasattr(pe, 'lineno'):
                self.parser.log('%s:%s:' % (pe.file, pe.lineno))
            if hasattr(pe, 'context'):
                self.parser.log('\n'.join(pe.context))
            if str(pe):
                self.parser.log(str(pe))
            raise
        except CIMError, ce:
            if hasattr(ce, 'file_line'):
                self.parser.log('Fatal Error: %s:%s' % (ce.file_line[0], 
                                                        ce.file_line[1]))
            else:
                self.parser.log('Fatal Error:')
            self.parser.log('%s%s' % (_errcode2string(ce.args[0]), 
                    ce.args[1] and ': '+ce.args[1] or ''))
            raise

    def compile_file(self, filename, ns):
        """Compile MOF from a file.

        Arguments:
        filename -- The file to read MOF from
        ns -- The CIM namespace
        """

        if self.parser.verbose:
            self.parser.log('Compiling file ' + filename)
        f = open(filename, 'r')
        mof = f.read()
        f.close()

        return self.compile_string(mof, ns, filename=filename)

    def find_mof(self, classname):
        """Find a MOF file corresponding to a CIM class name.  The search_paths
        provided to __init__() are searched recursively.

        Arguments:
        classname -- The name of the class to look for
        """

        classname = classname.lower()
        for search in self.parser.search_paths:
            for root, dirs, files in os.walk(search):
                for file_ in files:
                    if file_.endswith('.mof') and \
                            file_[:-4].lower() == classname:
                        return root + '/' + file_
        return None

    def rollback(self, verbose=False):
        self.handle.rollback(verbose=verbose)

def _build():
    yacc.yacc(optimize=_optimize, tabmodule=_tabmodule)
    lex.lex(optimize=_optimize, lextab=_lextab)


if __name__ == '__main__':
    from optparse import OptionParser
    usage = 'usage: %prog -n <namespace> [options] <MOF file> ...'
    oparser = OptionParser(usage=usage)
    oparser.add_option('-s', '--search', dest='search', 
            help='Search path to find missing schema elements.  This option can be present multiple times.', 
            metavar='Path', action='append')
    oparser.add_option('-n', '--namespace', dest='ns', 
            help='Specify the namespace', metavar='Namespace')
    oparser.add_option('-u', '--url', dest='url', 
            help='URL to the CIM Server', metavar='URL', 
            default='/var/run/tog-pegasus/cimxml.socket')
    oparser.add_option('-v', '--verbose',
            action='store_true', dest='verbose', default=False,
            help='Print more messages to stdout')
    oparser.add_option('-r', '--remove',
            action='store_true', dest='remove', default=False,
            help='Remove elements found in MOF, instead of create them')
    oparser.add_option('-l', '--username',
            dest='username', metavar='Username',
            help='Specify the username')
    oparser.add_option('-p', '--password', 
            dest='password', metavar='Password',
            help='Specify the password')

    (options, args) = oparser.parse_args()
    search = options.search
    if not args:
        oparser.error('No input files given for parsing')
    if options.ns is None: 
        oparser.error('No namespace given')

    passwd = options.password
    if options.username and not passwd:
        passwd = getpass('Enter password for %s: ' % options.username)
    if options.username:
        conn = WBEMConnection(options.url, (options.username, passwd))
    else:
        conn = WBEMConnection(options.url)
    if options.remove:
        conn = MOFWBEMConnection(conn=conn)
    #conn.debug = True
    conn.default_namespace = options.ns
    if search is None:
        search = []

    search = [os.path.abspath(x) for x in search]
    for fname in args:
        path = os.path.abspath(os.path.dirname(fname))
        for spath in search:
            if path.startswith(spath):
                break
        else:
            search.append(path)

    # if removing, we'll be verbose later when we actually remove stuff.
    # We don't want MOFCompiler to be verbose, as that would be confusing. 
    verbose = options.verbose and not options.remove

    mofcomp = MOFCompiler(handle=conn, search_paths=search, 
            verbose=verbose)

    try:
        for fname in args:
            if fname[0] != '/':
                fname = os.path.curdir + '/' + fname
            mofcomp.compile_file(fname, options.ns)
    except MOFParseError, pe:
        sys.exit(1)
    except CIMError, ce:
        sys.exit(1)

    if options.remove:
        conn.rollback(verbose=options.verbose)


