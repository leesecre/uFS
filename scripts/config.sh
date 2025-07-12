#!/bin/bash
# Microbenchmarks configurations

export UFSBENCH_IOSIZE="4K,16K,64K,256K"
export UFSBENCH_NUMAPP=2 # nr of applications to run concurrently, uFS supports up to 10

# export UFSBENCH_FILESIZE=$((5 * 1024 * 1024 * 1024)) # File size for microbenchmarks
export UFSBENCH_FILESIZE=$((1 * 1024 * 1024 * 1024)) # 1GB

# export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024)) # Latency benchmarks total size
export UFSBENCH_LAT_TOTAL_SIZE=$((256 * 1024 * 1024)) # 256MB


## Workload definitions: (*_L means latency benchmarks)
##   RDPR,RDPR_L   - Random read
##   RDPS,RDPS_L   - Sequential read
##   ADPS,ADPS_L   - Sequential append write
##   WDPS,WDPS_L   - Sequential overwrite
##   WDPR,WDPR_L   - Random overwrite

export UFSBENCH_WORKLOADS="RDPR,RDPR_L,RDPS,RDPS_L"
# export UFSBENCH_WORKLOADS="RDPR,ADPS,WDPS,WDPR,RDPR_L,ADPS_L,WDPS_L,WDPR_L"


# uFS make files on every running, which takes a long time.
# This option only prepares data once, and reuses it for every run.
# [WARN] uFS/oxbow is not tested with this option yet.
export PREPARE_DATA_ONLY_ONCE="1"