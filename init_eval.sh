#!/bin/bash

cp ./record_cpu_util.py ~/workspace/uFS-bench/filebench/
cp ./record_cpu_util.py ~/workspace/uFS-bench/FS_microbench/

cp ./run_varmail_ext4.py ~/workspace/uFS-bench/filebench/scripts/
cp ./run_varmail_ufs.py ~/workspace/uFS-bench/filebench/scripts/
cp ./run_webserver_ufs.py ~/workspace/uFS-bench/filebench/scripts/
cp ./run_webserver_ext4.py ~/workspace/uFS-bench/filebench/scripts/
cp ./cfs_bench/exprs/artifact_eval/run-fs_micro.sh ~/workspace/uFS/cfs_bench/exprs/artifact_eval/run-fs_micro.sh
cp ./run_fs_micro_all_ext4.py ~/workspace/uFS-bench/FS_microbench/scripts/
cp ./run_fs_micro_all_ufs.py ~/workspace/uFS-bench/FS_microbench/scripts/
cp -r ./FS_microbench ~/workspace/uFS-bench/
