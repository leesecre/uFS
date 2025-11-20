#!/bin/bash
# Microbenchmarks configurations

## Workload definitions: (*_L means latency benchmarks)
##   RDPR,RDPR_L   - Random read
##   RDPS,RDPS_L   - Sequential read
##   ADPS,ADPS_L   - Sequential append write
##   WDPS,WDPS_L   - Sequential overwrite
##   WDPR,WDPR_L   - Random overwrite
# export UFSBENCH_WORKLOADS="ADPS_L,WDPS_L,WDPR_L,RDPR_L,RDPS_L" # Latency
export UFSBENCH_WORKLOADS="ADPS,WDPR,WDPS,RDPR,RDPS" # Throughput

# export UFSBENCH_IOSIZE="1K,4K,16K,64K,256K,512K" # Latency
export UFSBENCH_IOSIZE="4K,16K,64K,256K" # Throughput

# export UFSBENCH_NUMAPP="1" # nr of applications to run concurrently, uFS supports up to 10
export UFSBENCH_NUMAPP="16" # nr of applications to run concurrently, uFS supports up to 10

# export UFSBENCH_FILESIZE=$((5 * 1024 * 1024 * 1024)) # File size for microbenchmarks
# export UFSBENCH_FILESIZE=$((1 * 1024 * 1024 * 1024)) # 1GB (Latency)
export UFSBENCH_FILESIZE=$((2 * 1024 * 1024 * 1024)) # 2GB (Throughput)

export UFSBENCH_SYNC_OP=131072
# export UFSBENCH_SYNC_OP=-1

# export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024)) # Latency benchmarks total size
# export UFSBENCH_LAT_TOTAL_SIZE=$((128 * 1024 * 1024)) # 128MB
export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024)) # 1GB

# Enable perf, latency benchmark automatically disable perf
export UFSBENCH_ENBALE_PERF="1" # comment out to disable perf

# uFS make files on every running, which takes a long time.
# This option only prepares data once, and reuses it for every run.
# [WARN] uFS/oxbow is not tested with this option yet.
export PREPARE_DATA_ONLY_ONCE="1"

### LevelDB configurations ###
export LEVELDB_WORKLOAD="all"
# export LEVELDB_WORKLOAD="a" # one of a,b,c,d,e,f

### Oxbow Configurations ###
# export OXBOW_HOST_JOURNALING="1"
# export OXBOW_USE_VM_ENV="1"

######## Oxbow LevelDB snapshot settings #########

# Do not set both at the same time. (Cf. run_ldb_oxbow.py)
export LDB_OXB_CREATE_SNAP=1 # Create a snapshot of db.
export LDB_OXB_LOAD_SNAP=0 # Use a snapshot instead of filling db.

### Ext4 Configuration ###
export EXT4_JNL_SIZE=40000 # Around 40GB journal size (max allowed by ext4, in MB)
