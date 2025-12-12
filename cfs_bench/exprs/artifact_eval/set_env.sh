#!/bin/bash

export AE_SSD_NAME="nvme0n1"
export CFS_ROOT_DIR="${HOME}/workspace/uFS"
export AE_WORK_DIR="$CFS_ROOT_DIR"
export AE_REPO_DIR="$CFS_ROOT_DIR"
export AE_BENCH_REPO_DIR="$AE_WORK_DIR/oxbow-uFS_bench"
export AE_SCRIPT_DIR="$AE_REPO_DIR/cfs_bench/exprs/artifact_eval"
export AE_CMPL_THREADS="15"  # avoid too many threads causing OOM