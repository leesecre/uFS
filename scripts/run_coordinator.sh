#!/bin/bash
COORDINATOR_CMD="/home/yulistic/oxbow/bench/uFS/cfs_bench/build/bins/cfs_bench_coordinator -n 1"

sudo rm -rf /dev/shm/coordinator
$COORDINATOR_CMD
