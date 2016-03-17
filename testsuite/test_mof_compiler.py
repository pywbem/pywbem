#!/usr/bin/env python
#

from __future__ import print_function
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

from pywbem.cim_operations import CIMError
from pywbem.mof_compiler import MOFCompiler, MOFWBEMConnection, MOFParseError
from pywbem.cim_constants import *

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

if __name__ == '__main__':
    unittest.main()
