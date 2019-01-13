#!/bin/bash
#
# Shell script that runs the run_uprint.py script in different scenarios.
# If the tests succeed, this script exits with exit code 0.

function run_test {
  cmd="$@"

  echo "Running: $cmd"

  sh -c "$cmd" 2>$err_log
  rc=$?

  if [[ $rc != 0 ]]; then
    echo "Error: Test failed with rc=$rc for: $cmd"
    echo "=== begin of stderr ==="
    cat $err_log
    echo "=== end of stderr ==="
    exit $rc
  else
    echo "Success."
    if [ -s $err_log ]; then
        # In this case, stderr may contain debug messages
        echo "Debug messages in this run:"
        cat $err_log
    fi
  fi
}

mydir=$(dirname $0)
err_log="$mydir/test_uprint_err.log"
out_log="$mydir/test_uprint_out.log"

run_test "python $mydir/run_uprint.py small"
run_test "python $mydir/run_uprint.py small >/dev/null"
run_test "python $mydir/run_uprint.py small >$out_log"

run_test "python $mydir/run_uprint.py ucs2 >/dev/null"
run_test "python $mydir/run_uprint.py ucs2 >$out_log"

run_test "python $mydir/run_uprint.py all >/dev/null"
run_test "python $mydir/run_uprint.py all >$out_log"
