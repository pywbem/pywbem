# Test mof_compiler creation and removal of a collection of MOF in
# a single file
# This is a very limited simplistic test.  It simply runs the script
# mof_compiler twice, once to build the test mof into defined server and
# a second time to remove it.  The only validation is that the scripts
# run without error.
# Further, it assumes that the WBEMServer is running, uses http, and is
# at localhost.. It does this twice to confirm that everything was removed
# on the first remove.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo DIR = $DIR
PYWBEM_ROOT_DIR=$DIR/../../

MOF_FILE=$PYWBEM_ROOT_DIR/tests/unittest/pywbem/test.mof
SCHEMA=$PYWBEM_ROOT_DIR/tests/schema/mofFinal2.51.0/
SERVER_URL=http://localhost
# To get verbose output, set VERBOSE=-v
VERBOSE=""
NAMESPACE=root/SampleProvider

mof_compiler -s $SERVER_URL $VERBOSE -I $SCHEMA $MOF_FILE
mof_compiler -s $SERVER_URL $VERBOSE -r -I $SCHEMA $MOF_FILE
mof_compiler -s $SERVER_URL $VERBOSE -I $SCHEMA $MOF_FILE
mof_compiler -s $SERVER_URL $VERBOSE -r -I $SCHEMA $MOF_FILE

mof_compiler -s $SERVER_URL $VERBOSE -I $SCHEMA $MOF_FILE -n $NAMESPACE
mof_compiler -s $SERVER_URL $VERBOSE -r -I $SCHEMA $MOF_FILE -n $NAMESPACE
mof_compiler -s $SERVER_URL $VERBOSE -I $SCHEMA $MOF_FILE -n $NAMESPACE
mof_compiler -s $SERVER_URL $VERBOSE -r -I $SCHEMA $MOF_FILE -n $NAMESPACE
