"""
Definition of the DMTF MOF Schema to be used in this testsuite.

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

2. Delete the SCHEMA_DIR (testsuite/schema)

3. Execute testsuite/test_mof_compiler.py. This should cause the new schema
   to be downloaded and expanded as part of the test.

4. The first test should generate an error if the values for total number of
   classes or qualifiers have changed. Modify the  variables below to define
   the correct numbers and re-execute test_mof_compiler.
"""

# Change the following variables when a new version of the CIM Schema is used
# and remove the SCHEMA_DIR directory
# This defines the version and the location of the schema zip file on the
# DMTF web site.
# See the page http://www.dmtf.org/standards/cim if there are issues
# downloading a particular version.

MOF_ZIP_BN = 'cim_schema_2.48.0Final-MOFs.zip'
MOF_ZIP_URL = 'http://www.dmtf.org/standards/cim/cim_schema_v2480/' + \
    MOF_ZIP_BN
SCHEMA_MOF_BN = 'cim_schema_2.48.0.mof'

# Expected total of qualifiers and classes in the DMTF Schema.
# These may change for each schema release and will need to be manually
# modified here to correctly execute the tests.
TOTAL_QUALIFIERS = 70
TOTAL_CLASSES = 1630
