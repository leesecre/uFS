#!/bin/bash
NUM_APP="2"
COORDINATOR_CMD="/home/yulistic/oxbow/bench/uFS/cfs_bench/build/bins/cfs_bench_coordinator -n $NUM_APP"

sudo rm -rf /dev/shm/coordinator
$COORDINATOR_CMD
