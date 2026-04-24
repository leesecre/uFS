#! /bin/bash
# This script for compiling other benchmarks rather than uFS_bench; microbench.
set -e

SANITIZE=0 # Enable sanitizer for leveldb.

if [ -z "$OXBOW_ENV_SOURCED" ]; then
	echo "Do source set_env.sh first. in oxbow root directory"
	exit
fi

# ───────────────────────────────────────────────
# Parse arguments
FS_TYPE=$1
BENCH_TYPE=$2

# Check FS_TYPE
if [[ -z "$FS_TYPE" ]]; then
  echo "Error: FS_TYPE is required (ufs, oxbow, ext4)"
  exit 1
elif [[ "$FS_TYPE" != "ufs" && "$FS_TYPE" != "oxbow" && "$FS_TYPE" != "ext4" ]]; then
  echo "Error: Invalid FS_TYPE '$FS_TYPE'. Allowed: ufs, oxbow, ext4"
  exit 1
fi

# Set default for BENCH_TYPE if not provided
if [[ -z "$BENCH_TYPE" ]]; then
  BENCH_TYPE="all"
elif [[ "$BENCH_TYPE" != "micro" && "$BENCH_TYPE" != "filebench" && "$BENCH_TYPE" != "leveldb" && "$BENCH_TYPE" != "all" ]]; then
  echo "Error: Invalid BENCH_TYPE '$BENCH_TYPE'. Allowed: micro, filebench, leveldb, all"
  exit 1
fi

UFS_APP_BENCH="$BENCH_UFS/oxbow-uFS_bench"

function cmpl_microbench() {
    if [ "$1" != "ufs" ]; then
	    CMAKE_ARG="-DONLY_POSIX=ON"
	    # CMAKE_ARG="-DONLY_POSIX=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo"
	    # CMAKE_ARG="-DONLY_POSIX=ON -DCMAKE_BUILD_TYPE=Debug"
    fi
    cd "$BENCH_UFS/cfs_bench"
    rm -rf build
    mkdir -p build && cd build
    cmake .. ${CMAKE_ARG}
    make -j
}

function cmpl_filebench() {
    # TODO: uFS filebench is not supported yet
    # uFS requires different compilation options for each workloads
    # If you want to run filebench with uFS, please use origin branch of uFS
    if [ "$1" == "ufs" ]; then
	    echo "ufs filebench is not supported yet"
        exit 1
    fi

    cd "$UFS_APP_BENCH/filebench"
    libtoolize
    aclocal
    autoheader
    automake --add-missing
    autoconf
    ./configure
    make clean
    make # filebench not recommend -j option
    sudo make install
}

function cmpl_leveldb() {

    # TODO: uFS leveldb is not supported yet
    # uFS requires different compilation options for each workloads
    # If you want to run filebench with uFS, please use origin branch of uFS
    if [ "$1" == "ufs" ]; then
	    echo "ufs leveldb is not supported yet"
        exit 1
    fi

    # oxbow will not use copying the database files (no optimization for loading)
    # this not affect the evaluating the performance of LevelDB
    if [ "$1" = "oxbow" ]; then
	    LDB_CMAKE_CFS_ARG="-DLEVELDB_JL_LIBCFS=OFF -DLEVELDB_JL_OXBOW=ON"
    else
        LDB_CMAKE_CFS_ARG="-DLEVELDB_JL_LIBCFS=OFF -DLEVELDB_JL_OXBOW=OFF"
    fi

    # Optional sanitizer flags (enabled when SANITIZE=1)
    local SAN_FLAGS=""
    local BUILD_TYPE="Release"
    # local BUILD_TYPE="Debug"
    if [[ "$SANITIZE" == "1" ]]; then
        SAN_FLAGS="-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
    fi

    cd "$UFS_APP_BENCH/leveldb-1.22"
    sudo rm -rf build
    mkdir build && cd build
    cmake ${LDB_CMAKE_CFS_ARG} \
        -DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
        -DCMAKE_C_FLAGS="${SAN_FLAGS}" \
        -DCMAKE_CXX_FLAGS="${SAN_FLAGS}" \
        -DCMAKE_EXE_LINKER_FLAGS="${SAN_FLAGS}" \
        ..
    make -j
}

# ───────────────────────────────────────────────
# Execute based on BENCH_TYPE
if [[ "$BENCH_TYPE" == "micro" || "$BENCH_TYPE" == "all" ]]; then
  echo "Building microbench..."
  cmpl_microbench "$FS_TYPE"
fi

if [[ "$BENCH_TYPE" == "filebench" || "$BENCH_TYPE" == "all" ]]; then
  echo "Building filebench..."
  cmpl_filebench "$FS_TYPE"
fi

if [[ "$BENCH_TYPE" == "leveldb" || "$BENCH_TYPE" == "all" ]]; then
  echo "Building leveldb..."
  cmpl_leveldb "$FS_TYPE"
fi
