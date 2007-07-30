#!/bin/sh

# Parse command line

usage() {
    echo "Usage: runtests.sh [-p PYTHON] [-- ARGS]"
    echo ""
    echo "Where PYTHON is the python binary to use (default 'python')"
    echo "and ARGS are passed as command line parameters to the test"
    echo "scripts.  (The '--' must separate runtest parameters from"
    echo "test script parameters)."
}

PYTHON="python"

while getopts "p:" options; do
    case $options in
	p) PYTHON=$OPTARG
	   ;;
	?) usage
	   exit 1
	   ;;
    esac
done

shift `expr $OPTIND - 1`

if [ "$1" = "all" ]; then
    PYTHON="python2.3 python2.4"
fi

# Run tests

failed=0

for test in test_*.py; do
    for python in $PYTHON; do
	echo ====================
	echo $python $test
	echo ====================
	$python $test "$@"
	if [ $? != 0 ]; then
	    failed=1
	    break
	fi
   done
done

# Display a message and set exit code appropriately

if [ $failed = 1 ]; then
    echo TESTS FAILED
    exit $failed
fi

echo TESTS PASSED
