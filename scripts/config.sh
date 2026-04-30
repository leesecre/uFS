#!/bin/bash
# Microbenchmarks configurations
RUN_LATENCY="1" # 0: throughput, 1: latency

## Workload definitions: (*_L means latency benchmarks)
##   RDPR,RDPR_L   - Random read
##   RDPS,RDPS_L   - Sequential read
##   ADPS,ADPS_L   - Sequential append write
##   WDPS,WDPS_L   - Sequential overwrite
##   WDPR,WDPR_L   - Random overwrite

if [ "$RUN_LATENCY" = "1" ]; then
	export UFSBENCH_WORKLOADS="ADPS_L,WDPS_L,WDPR_L,RDPR_L,RDPS_L"

	export UFSBENCH_IOSIZE="1K,4K,16K,64K,256K,512K"

	# nr of applications to run concurrently, uFS supports up to 10
	export UFSBENCH_NUMAPP="1"

	# Latency benchmarks total size
	# export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024))
	# export UFSBENCH_LAT_TOTAL_SIZE=$((128 * 1024 * 1024)) # 128MB
	export UFSBENCH_LAT_TOTAL_SIZE=$((1 * 1024 * 1024 * 1024)) # 1GB

	# File size (it is used for preparation in latency benchmarks).
	export UFSBENCH_FILESIZE=$UFSBENCH_LAT_TOTAL_SIZE

else
	export UFSBENCH_WORKLOADS="ADPS,WDPR,WDPS,RDPR,RDPS"

	export UFSBENCH_IOSIZE="4K,16K,64K,256K"

	# Maximum number of concurrent benchmark applications. (uFS supports up to 10, oxbow/ext4 support up to 64)
	export UFSBENCH_NUMAPP="64"

	# File size (per file for throughput benchmarks).
	export UFSBENCH_FILESIZE=$((2 * 1024 * 1024 * 1024)) # 2GB (Throughput)
	# export UFSBENCH_FILESIZE=$((5 * 1024 * 1024 * 1024)) # uFS Default.

	# Total I/O size for throughput benchmarks.
	# This can be smaller than UFSBENCH_FILESIZE so that the benchmark
	# reads/writes only part of the file (e.g., 512MB out of 2GB).
	# export UFSBENCH_THR_TOTAL_SIZE=$((2 * 1024 * 1024 * 1024)) # 2GB
	# export UFSBENCH_THR_TOTAL_SIZE=$((512 * 1024 * 1024)) # 512MB
	# If you want to use the full file size as before, comment out the
	# above line and uncomment the following one:
	export UFSBENCH_THR_TOTAL_SIZE=$UFSBENCH_FILESIZE

fi

# Enable perf, latency micro benchmark automatically disable perf
export UFSBENCH_ENABLE_PERF="1" # comment out to disable perf

# Enable flamegraph generation. Requires UFSBENCH_ENABLE_PERF to be set.
# When enabled, perf record will also collect call stacks (-g) so that a
# flamegraph SVG can be generated automatically after each run.
# Note that cfs_bench should be compiled with -DCMAKE_BUILD_TYPE=RelWithDebInfo
# or -DCMAKE_BUILD_TYPE=Debug to enable flamegraph generation.
# export UFSBENCH_ENABLE_FLAMEGRAPH="1" # comment out to disable flamegraph

# Path to Brendan Gregg's FlameGraph scripts (stackcollapse-perf.pl,
# flamegraph.pl). Required when UFSBENCH_ENABLE_FLAMEGRAPH is set.
# Clone from: https://github.com/brendangregg/FlameGraph
export UFSBENCH_FLAMEGRAPH_DIR="$HOME/FlameGraph"
# export UFSBENCH_FLAMEGRAPH_DIR="/home/yulistic/oxbow/tools/flamegraph/FlameGraph"

export UFSBENCH_SYNC_OP=131072
# export UFSBENCH_SYNC_OP=-1 # Only one fsync at the end.

# uFS make files on every running, which takes a long time.
# This option only prepares data once, and reuses it for every run.
# [WARN] uFS/oxbow is not tested with this option yet.
export PREPARE_DATA_ONLY_ONCE="1"

# When enabled (1/true/yes), reuse existing data for non-append benchmarks
# and skip mkfs + data preparation when applicable.
# If append workloads (e.g., ADPS/ADPS_L) are included, reuse is disabled automatically.
export MICROBENCH_REUSE_DATA="1"

# Force reuse even for workloads that normally require prepared data
# (e.g., RDPS/RDPR/WDPS/WDPR). Use only when the existing filesystem already
# has the required bench_f_* files with sufficient size.
# export MICROBENCH_FORCE_REUSE_DATA="1"

### Filebench configurations ###
# Comma-separated list of workloads to run for filebench benchmark.
# Example: "varmail,webserver"
export FILEBENCH_WORKLOAD="webserver,varmail"

### LevelDB configurations ###
export LEVELDB_WORKLOAD="all"
# export LEVELDB_WORKLOAD="d,e,f" # pick some of a,b,c,d,e,f (comma separate)

# Address Sanitizer library path. (for leveldb)
# export ASAN_LIB=$(gcc -print-file-name=libasan.so)

### Oxbow Configurations ###
# export OXBOW_HOST_JOURNALING="1"
# export OXBOW_USE_VM_ENV="1"

######## Oxbow LevelDB snapshot settings #########

# Do not set both at the same time. (Cf. run_ldb_oxbow.py)
export LDB_OXB_CREATE_SNAP=0 # Create a snapshot of db.
export LDB_OXB_LOAD_SNAP=0 # Use a snapshot instead of filling db.

# LevelDB snapshot size in MB for dd (bs=1M, total size = LDB_OXB_SNAP_SIZE_MB
# MB).
# It should be matched with File system area size. (cf. ext4_mkfs.c)
export LDB_OXB_SNAP_SIZE_MB=10240 # 10 GB.

### Ext4 Configuration ###
export EXT4_JNL_SIZE=40000 # Around 40GB journal size (max allowed by ext4, in MB)
