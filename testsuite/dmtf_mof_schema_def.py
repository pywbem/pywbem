"""
Definition of the DMTF MOF Schema to be used in this testsuite and the
code to install it if not already installed and unzipped.

The version defined below will be installed in the directory SCHEMA_DIR
(testsuite/schema) if that directory is empty or the file does not exist.

Otherwise, the tests will be executed with that defined version of the
schema.

NOTE: The zip expansion is NOT committed to git, just the original zip file.

To change the schema used:

1. Change the following variables to match the DMTF schema to be used
    (MOF_ZIP_BN, MOF_ZIP_URL, SCHEMA_MOF_BN)
    NOTE: The BN, URL, and MOF_BN will change between versions. The V2xxx in the
        URL must be updated and the version number in both MOF_ZIP_BN and
        SCHEMA_MOF_BIN updated.
    See the page http://www.dmtf.org/standards/cim if there are issues
    downloading a particular schema version.

2. Delete the SCHEMA_DIR (testsuite/schema). Be sure to delete the directory
   to be sure the new schema gets downloaded and correctly expanded.

3. Execute testsuite/test_mof_compiler.py. This should cause the new schema
   to be downloaded and expanded as part of the test.

4. The first test should generate an error if the values for total number of
   classes or qualifiers have changed. Modify the  variables below to define
   the correct numbers and re-execute test_mof_compiler.
   NOTE: We are keeping some history of the counts for previous versions of
   the schema (see the comments at the end of this file)
"""

import os
from zipfile import ZipFile
import six

if six.PY2:
    # pylint: disable=wrong-import-order
    from urllib2 import urlopen
else:
    # pylint: disable=wrong-import-order
    from urllib.request import urlopen

# Change the following variables when a new version of the CIM Schema is used
# and remove the SCHEMA_DIR directory
# This defines the version and the location of the schema zip file on the
# DMTF web site.
# See the page http://www.dmtf.org/standards/cim if there are issues
# downloading a particular version.

# Location of the schema for use by test_mof_compiler.
# This should not change unless you intend to use another schema directory
SCRIPT_DIR = os.path.dirname(__file__)
SCHEMA_DIR = os.path.join(SCRIPT_DIR, 'schema')
SCHEMA_MOF_DIR = os.path.join(SCHEMA_DIR, 'mof')

DMTF_SCHEMA_VERSION = 'cim_schema_2.49.0'
MOF_ZIP_BN = DMTF_SCHEMA_VERSION + 'Final-MOFs.zip'
MOF_ZIP_URL = 'http://www.dmtf.org/standards/cim/cim_schema_v2490/' + MOF_ZIP_BN
SCHEMA_MOF_BN = DMTF_SCHEMA_VERSION + '.mof'

# DMTF Schema zip filename and mof filename
MOF_ZIP_FN = os.path.join(SCHEMA_DIR, MOF_ZIP_BN)
SCHEMA_MOF_FN = os.path.join(SCHEMA_MOF_DIR, SCHEMA_MOF_BN)

# Expected total of qualifiers and classes in the DMTF Schema.
# These may change for each schema release and will need to be manually
# modified here to correctly execute the tests.
# 2.49.0
TOTAL_QUALIFIERS = 70
TOTAL_CLASSES = 1631

# Qualifier and Class counts for previous DMTF schema.
# 2.48.0
# TOTAL_QUALIFIERS = 70
# TOTAL_CLASSES = 1630


def install_dmtf_schema():
    """
    Install the DMTF schema if it is not already installed.  All the
    definitions of the installation are in the module variables.
    The user of ths should need
    """
    first = True

    if not os.path.isdir(SCHEMA_DIR):
        if first:
            print("")
            first = False
        print("Creating directory for CIM Schema archive: %s" % SCHEMA_DIR)
        os.mkdir(SCHEMA_DIR)

    if not os.path.isfile(MOF_ZIP_FN):
        if first:
            print("")
            first = False
        print("Downloading CIM Schema archive from: %s" % MOF_ZIP_URL)
        ufo = urlopen(MOF_ZIP_URL)
        with open(MOF_ZIP_FN, 'w') as fp:
            for data in ufo:
                fp.write(data)

    if not os.path.isdir(SCHEMA_MOF_DIR):
        if first:
            print("")
            first = False
        print("Creating directory for CIM Schema MOF files: %s" %
              SCHEMA_MOF_DIR)
        os.mkdir(SCHEMA_MOF_DIR)

    if not os.path.isfile(SCHEMA_MOF_FN):
        if first:
            print("")
            first = False
        print("Unpacking CIM Schema archive: %s" % MOF_ZIP_FN)
        try:
            zfp = ZipFile(MOF_ZIP_FN, 'r')
            nlist = zfp.namelist()
            for file_ in nlist:
                dfile = os.path.join(SCHEMA_MOF_DIR, file_)
                if dfile[-1] == '/':
                    if not os.path.exists(dfile):
                        os.mkdir(dfile)
                else:
                    with open(dfile, 'w+b') as dfp:
                        dfp.write(zfp.read(file_))
        finally:
            zfp.close()
