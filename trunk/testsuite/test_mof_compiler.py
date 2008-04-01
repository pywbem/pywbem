#!/usr/bin/env python
#

from comfychair import main, TestCase, NotRunError
from pywbem import *

from pywbem.mof_compiler import MOFCompiler, MOFWBEMConnection, ParseError

from urllib import urlretrieve, urlopen
from time import time

import os
import sys
from zipfile import ZipFile
from tempfile import TemporaryFile

ns = 'root/test'

cwd = os.getcwd()

# Change the mofurl when new schema is released.
mofurl = 'http://www.dmtf.org/standards/cim/cim_schema_v2171/cimv217Experimental-MOFs.zip'

class MOFTest(TestCase):
    """A base class that creates a MOF compiler instance"""

    def setup(self):
        """Create the MOF compiler."""

        def moflog(msg):
            print >> self.logfile, msg

        self.logfile = open('moflog.txt', 'w')

        self.mofcomp = MOFCompiler(MOFWBEMConnection(), 
                search_paths=['schema'], verbose=False,
                log_func=moflog)
        os.chdir(cwd)


class TestFullSchema(MOFTest):

    def runtest(self):
        t = time()
        self.mofcomp.compile_file('schema/cimv217.mof', ns)
        print 'elapsed: %f  ' % (time() - t),
        self.assert_equal(len(self.mofcomp.handle.qualifiers[ns]), 71)
        self.assert_equal(len(self.mofcomp.handle.classes[ns]), 1596)
        #print self.mofcomp.handle.classes[ns]['CIM_UnsignedCredential'].properties['OtherPublicKeyEncoding'].qualifiers['Description']

class TestAliases(MOFTest):
    
    def runtest(self):
        self.mofcomp.compile_file('test.mof', ns)

class TestSchemaError(MOFTest):
    
    def runtest(self):
        self.mofcomp.parser.search_paths = []
        try:
            self.mofcomp.compile_file('schema/System/CIM_ComputerSystem.mof', ns)
        except CIMError, ce:
            self.assert_equal(ce.args[0], CIM_ERR_FAILED)
            self.assert_equal(ce.file_line[0], 'schema/System/CIM_ComputerSystem.mof')
            self.assert_equal(ce.file_line[1], 21)

        self.mofcomp.compile_file('schema/qualifiers.mof', ns)
        try:
            self.mofcomp.compile_file('schema/System/CIM_ComputerSystem.mof', ns)
        except CIMError, ce:
            self.assert_equal(ce.args[0], CIM_ERR_INVALID_SUPERCLASS)
            self.assert_equal(ce.file_line[0], 'schema/System/CIM_ComputerSystem.mof')
            self.assert_equal(ce.file_line[1], 177)

class TestSchemaSearch(MOFTest):
    def runtest(self):
        self.mofcomp.compile_file('schema/System/CIM_ComputerSystem.mof', ns)
        ccs = self.mofcomp.handle.GetClass('CIM_ComputerSystem', 
                LocalOnly=False, IncludeQualifiers=True)
        self.assert_equal(ccs.properties['RequestedState'].type, 'uint16')
        self.assert_equal(ccs.properties['Dedicated'].type, 'uint16')
        cele = self.mofcomp.handle.GetClass('CIM_EnabledLogicalElement', 
                LocalOnly=False, IncludeQualifiers=True)
        self.assert_equal(cele.properties['RequestedState'].type, 'uint16')


class TestParseError(MOFTest):
    def runtest(self):
        file = 'testmofs/parse_error01.mof'
        try:
            self.mofcomp.compile_file(file, ns)
        except ParseError, pe:
            self.assert_equal(pe.file, file)
            self.assert_equal(pe.lineno, 16)
            self.assert_equal(pe.context[5][1:5], '^^^^')
            self.assert_equal(pe.context[4][1:5], 'size')

        file = 'testmofs/parse_error02.mof'
        try:
            self.mofcomp.compile_file(file, ns)
        except ParseError, pe:
            self.assert_equal(pe.file, file)
            self.assert_equal(pe.lineno, 6)
            self.assert_equal(pe.context[5][7:13], '^^^^^^')
            self.assert_equal(pe.context[4][7:13], 'weight')

class TestRefs(MOFTest):
    def runtest(self):
        self.mofcomp.compile_file('testmofs/test_refs.mof', ns)

#################################################################
# Main function
#################################################################

tests = [
    TestAliases,
    TestRefs,
    TestSchemaError,
    TestSchemaSearch, 
    TestParseError, 
    TestFullSchema,
    ]

if __name__ == '__main__':

    mofbname = mofurl.split('/')[-1]

    if not os.path.isdir('schema'):
        os.mkdir('schema')

        tfo = TemporaryFile()
        ufo = urlopen(mofurl)
        clen = int(ufo.info().getheader('Content-Length'))
        offset = 0
        ppct = -1
        for data in ufo:
            offset+= len(data)
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
            file = nlist[i]
            dfile = 'schema/%s' % file
            if dfile[-1] == '/':
                if not os.path.exists(dfile):
                    os.mkdir(dfile)
            else:
                fo = open(dfile, 'w')
                fo.write(zf.read(file))
                fo.close()
        tfo.close()
        print ''

    main(tests)

