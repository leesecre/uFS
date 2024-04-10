#!/bin/bash

## cpu utils
cp ./ext_scripts/record_cpu_util.py ~/workspace/uFS-bench/filebench/
cp ./ext_scripts/record_cpu_util.py ~/workspace/uFS-bench/FS_microbench/

## filebench
cp ./ext_scripts/run_varmail_ufs.py ~/workspace/uFS-bench/filebench/scripts/
cp ./ext_scripts/run_varmail_ext4.py ~/workspace/uFS-bench/filebench/scripts/
cp ./ext_scripts/run_webserver_ufs.py ~/workspace/uFS-bench/filebench/scripts/
cp ./ext_scripts/run_webserver_ext4.py ~/workspace/uFS-bench/filebench/scripts/
cp ./ext_scripts/run_fileserver_ufs.py ~/workspace/uFS-bench/filebench/scripts/
cp ./ext_scripts/run_fileserver_ext4.py ~/workspace/uFS-bench/filebench/scripts/

## FS_micro
cp ./cfs_bench/exprs/artifact_eval/run-fs_micro.sh ~/workspace/uFS/cfs_bench/exprs/artifact_eval/run-fs_micro.sh
cp -r ./FS_microbench ~/workspace/uFS-bench/
cp ./ext_scripts/run_fs_micro_all_ext4.py ~/workspace/uFS-bench/FS_microbench/scripts/
cp ./ext_scripts/run_fs_micro_all_ufs.py ~/workspace/uFS-bench/FS_microbench/scripts/
