#!/bin/bash
# Run the run_response_performance.py script for some parameter sets and capture the results.

runid=${1:-$(date "+%Y%m%d_%H%M%S")}

function run() {
    profile=$1
    insts=$2
    size=$3
    echo "Running run_response_performance.py with profile $profile for $insts instances of size $size B ..."
    logfile=perf_${runid}_${profile}_${insts}_${size}.log
    cmd="python tests/manualtest/run_response_performance.py -p $profile -c $insts -s $size >$logfile 2>&1"
    echo "$cmd"
    start=$(date "+%Y%m%d%H%M%S")
    eval "$cmd"
    python -c "from datetime import datetime; diff=(datetime.now() - datetime.strptime('$start', '%Y%m%d%H%M%S')); print('Elapsed time: %.1f s'%diff.total_seconds())"
    echo "Output is in: $logfile"
}


run table 1000 500
run stack 1000 500
run table 10000 500
run stack 10000 500
# run table 100000 500
# run stack 100000 500
