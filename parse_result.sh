#!/bin/bash

## varmail
python3 cfs_bench/exprs/filebench_plot/varmail/parse_log.py ext4 ~/uFS/AE_DATA/DATA_filebench_varmail_ext4
python3 cfs_bench/exprs/filebench_plot/varmail/parse_log.py ufs ~/uFS/AE_DATA/DATA_filebench_varmail_ufs

## webserver
python3 cfs_bench/exprs/filebench_plot/webserver/parse_log.py ext4 ~/uFS/AE_DATA/DATA_filebench_webserver_ext4
python3 cfs_bench/exprs/filebench_plot/webserver/parse_log.py ufs ~/uFS/AE_DATA/DATA_filebench_webserver_ufs
