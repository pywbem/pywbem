#!/usr/bin/env python
#

import sys
import os
from time import time
from urllib import urlopen
from zipfile import ZipFile
from tempfile import TemporaryFile
import unittest
import pytest

from pywbem.cim_operations import CIMError
from pywbem.mof_compiler import MOFCompiler, MOFWBEMConnection, MOFParseError
from pywbem.cim_constants import *

ns = 'root/test'

SCRIPT_DIR = os.path.dirname(__file__)
SCHEMA_DIR = os.path.join(SCRIPT_DIR, 'schema')

# Change the mofurl when new schema is released.
mofurl = 'http://www.dmtf.org/standards/cim/cim_schema_v220/' \
         'cim_schema_2.20.0Experimental-MOFs.zip'

def setUpModule():

    if not os.path.isdir(SCHEMA_DIR):

        print "\nDownloading CIM Schema into %s ..." % SCHEMA_DIR

        os.mkdir(SCHEMA_DIR)

        mofbname = mofurl.split('/')[-1]

        tfo = TemporaryFile()
        ufo = urlopen(mofurl)
        clen = int(ufo.info().getheader('Content-Length'))
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
        print ''

        zf = ZipFile(tfo, 'r')
        nlist = zf.namelist()
        for i in xrange(0, len(nlist)):
            sys.stdout.write('\rUnpacking %s: %d%% ' % (mofbname,
                                                        100*(i+1)/len(nlist)))
            sys.stdout.flush()
            file_ = nlist[i]
            dfile = os.path.join(SCHEMA_DIR, file_)
            if dfile[-1] == '/':
                if not os.path.exists(dfile):
                    os.mkdir(dfile)
            else:
                fo = open(dfile, 'w')
                fo.write(zf.read(file_))
                fo.close()
        tfo.close()
        print ''


class MOFTest(unittest.TestCase):
    """A base class that creates a MOF compiler instance"""

    def setUp(self):
        """Create the MOF compiler."""

        def moflog(msg):
            print >> self.logfile, msg
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
            os.path.join(SCHEMA_DIR, 'cim_schema_2.20.0.mof'), ns)
        print 'elapsed: %f  ' % (time() - t),
        self.assertEqual(len(self.mofcomp.handle.qualifiers[ns]), 71)
        self.assertEqual(len(self.mofcomp.handle.classes[ns]), 1644)
        #print self.mofcomp.handle.classes[ns]['CIM_UnsignedCredential'].\
        #    properties['OtherPublicKeyEncoding'].qualifiers['Description']

class TestAliases(MOFTest):

    def test_all(self):
        self.mofcomp.compile_file(
            os.path.join(SCRIPT_DIR, 'test.mof'), ns)

class TestSchemaError(MOFTest):

    def test_all(self):
        self.mofcomp.parser.search_paths = []
        try:
            self.mofcomp.compile_file(os.path.join(
                                          SCHEMA_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'),
                                      ns)
        except CIMError, ce:
            self.assertEqual(ce.args[0], CIM_ERR_FAILED)
            self.assertEqual(ce.file_line[0],
                             os.path.join(
                                 SCHEMA_DIR,
                                 'System',
                                 'CIM_ComputerSystem.mof'))
            self.assertEqual(ce.file_line[1], 21)

        self.mofcomp.compile_file(os.path.join(
                                      SCHEMA_DIR,
                                      'qualifiers.mof'),
                                  ns)
        try:
            self.mofcomp.compile_file(os.path.join(
                                          SCHEMA_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'),
                                      ns)
        except CIMError, ce:
            self.assertEqual(ce.args[0], CIM_ERR_INVALID_SUPERCLASS)
            self.assertEqual(ce.file_line[0],
                             os.path.join(
                                 SCHEMA_DIR,
                                 'System',
                                 'CIM_ComputerSystem.mof'))
            self.assertEqual(ce.file_line[1], 177)

class TestSchemaSearch(MOFTest):

    def test_all(self):
        self.mofcomp.compile_file(os.path.join(
                                      SCHEMA_DIR,
                                      'System',
                                      'CIM_ComputerSystem.mof'),
                                  ns)
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
            self.mofcomp.compile_file(_file, ns)
        except MOFParseError, pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 16)
            self.assertEqual(pe.context[5][1:5], '^^^^')
            self.assertEqual(pe.context[4][1:5], 'size')

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error02.mof')
        try:
            self.mofcomp.compile_file(_file, ns)
        except MOFParseError, pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 6)
            self.assertEqual(pe.context[5][7:13], '^^^^^^')
            self.assertEqual(pe.context[4][7:13], 'weight')

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error03.mof')
        try:
            self.mofcomp.compile_file(_file, ns)
        except MOFParseError, pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 24)
            self.assertEqual(pe.context[5][53], '^')
            self.assertEqual(pe.context[4][53], '}')

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error04.mof')
        try:
            self.mofcomp.compile_file(_file, ns)
        except MOFParseError, pe:
            self.assertEqual(str(pe), 'Unexpected end of file')

class TestRefs(MOFTest):

    def test_all(self):
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_refs.mof'),
                                  ns)

if __name__ == '__main__':
    unittest.main()
