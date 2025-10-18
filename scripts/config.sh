#!/bin/bash
# Microbenchmarks configurations


export UFSBENCH_IOSIZE="4K"
# export UFSBENCH_IOSIZE="4K,16K,64K,256K"
export UFSBENCH_NUMAPP=1 # nr of applications to run concurrently, uFS supports up to 10

# export UFSBENCH_FILESIZE=$((5 * 1024 * 1024 * 1024)) # File size for microbenchmarks
# export UFSBENCH_FILESIZE=$((1 * 1024 * 1024 * 1024)) # 1GB
export UFSBENCH_FILESIZE=$((2 * 1024 * 1024 * 1024)) # 2GB

# export UFSBENCH_SYNC_OP=131072
export UFSBENCH_SYNC_OP=131072

# export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024)) # Latency benchmarks total size
# export UFSBENCH_LAT_TOTAL_SIZE=$((128 * 1024 * 1024)) # 128MB
export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024)) # 1GB

# Enable perf, latency benchmark automatically disable perf
export UFSBENCH_ENBALE_PERF="1" # comment out to disable perf

## Workload definitions: (*_L means latency benchmarks)
##   RDPR,RDPR_L   - Random read
##   RDPS,RDPS_L   - Sequential read
##   ADPS,ADPS_L   - Sequential append write
##   WDPS,WDPS_L   - Sequential overwrite
##   WDPR,WDPR_L   - Random overwrite

# export UFSBENCH_WORKLOADS="RDPR,RDPR_L,RDPS,RDPS_L"
# export UFSBENCH_WORKLOADS="WDPR"
export UFSBENCH_WORKLOADS="ADPS,WDPS,WDPR,RDPR,RDPS,ADPS_L,WDPS_L,WDPR_L,RDPR_L,RDPS_L"
# export UFSBENCH_WORKLOADS="RDPR,RDPS,RDPR_L,RDPS_L"


# uFS make files on every running, which takes a long time.
# This option only prepares data once, and reuses it for every run.
# [WARN] uFS/oxbow is not tested with this option yet.
export PREPARE_DATA_ONLY_ONCE="1"

# Oxbow setting
# export OXBOW_HOST_JOURNALING="1"
# export OXBOW_USE_VM_ENV="1"
