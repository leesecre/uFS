#!/usr/bin/env python3
# encoding: utf-8

import os
import sys
import time

import cfs_test_common as tc
import cfsmt_expr_read as mte_rd


def print_usage():
    print(
        'Usage: {} <ext4 | fsp> [cached] [share] [mpstat] [blk=N] [numapp=]'.format(
            sys.argv[0]))


if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

cur_is_fsp = None
cur_is_oxbow = None
if 'ext4' in sys.argv[1]:
    cur_is_fsp = False
    cur_dev_name = tc.get_kfs_dev_name()
elif 'fsp' in sys.argv[1]:
    cur_is_fsp = True
elif 'oxbow' in sys.argv[1]:
    cur_is_fsp = False
    cur_is_oxbow = True
else:
    print_usage()
    sys.exit(1)
print('is_fsp? - {}'.format(str(cur_is_fsp)))


cur_is_cached = False
cur_is_no_overlap = True
cur_is_dump_mpstat = False
cur_block_no = -1
cur_numapp = None
cur_is_share = False
#cur_perf_cmd = 'perf stat -d '
cur_perf_cmd = None
cur_is_throughput = True


if len(sys.argv) >= 3:
    for a in sys.argv[2:]:
        if 'cached' in a:
            cur_is_cached = True
            cur_is_no_overlap = False
        if 'mpstat' in a:
            cur_is_dump_mpstat = True
        if 'blk=' in a:
            cur_block_no = int(a.split('=')[1])
        if 'share' in a:
            cur_is_share = True
        if 'numapp=' in a:
            cur_numapp = int(a[a.index('=') + 1:])
        if 'latency' in a:
            cur_is_throughput = False

# print('is_cached? - {}'.format(str(cur_is_cached)))
# print('is_dump_mpstat? - {}'.format(str(cur_is_dump_mpstat)))
# print('block_no - {}'.format(cur_block_no))
# print('is_share_file? - {}'.format(str(cur_is_share)))

# Once block number is fixed, it is definitely a cached workload
if cur_block_no >= 0:
    assert(cur_is_cached)

BASE_DIR = os.environ.get("BENCH_UFS")
LOG_BASE = '{}/log_{}'.format(BASE_DIR, sys.argv[1])

if cur_numapp > 16:
    print(f"Error: cur_numapp ({cur_numapp}) must not be greater than 16.")
    cur_numapp = 16

if cur_is_throughput:
    if cur_is_fsp:
        num_app_list = [x for x in [1, 2, 4, 8, 10] if x < cur_numapp]
    else:
        num_app_list = [x for x in [1, 2, 4, 8, 10, 16] if x < cur_numapp]
    num_app_list.append(cur_numapp)
    num_app_list = sorted(num_app_list)
else:
    num_app_list  = [1]


for num_app in num_app_list:
    # Get benchmark type from environment variable or determine based on conditions
    if "RDPR" in os.environ.get("BENCHMARK_TYPE", ""):
        benchmark_type = "RDPR"

    print("=========================================")
    print(f"BENCHMARK: {benchmark_type}")
    print(f"NUM_APP: {num_app}")
    if cur_is_throughput:
        print(f"Random read throughput")
        CUR_ARKV_DIR = '{}_randread_throughput_app_{}'.format(LOG_BASE, num_app)
    else:
        print(f"Random read latency")
        CUR_ARKV_DIR = '{}_randread_latency_app_{}'.format(LOG_BASE, num_app)
    print("=========================================")

    cur_num_fs_wk_list = [(i + 1) for i in range(num_app)]
    if not cur_is_fsp:
        cur_num_fs_wk_list = [1]
    else:
        #cur_num_fs_wk_list = list(set([1, num_app]))
        cur_num_fs_wk_list = [num_app]
        pass
    if tc.use_single_worker():
        cur_num_fs_wk_list = [1]

    cur_log_dir = tc.get_proj_log_dir(tc.get_expr_user(),
                                    suffix=tc.get_ts_dir_name(),
                                    do_mkdir=True)
    # dump io stats for kernel fs
    cur_dump_io_stat = False
    # if not cur_is_fsp and not cur_is_oxbow:
    #     cur_dump_io_stat = True

    # stress sharing
    if cur_is_share:
        per_app_fname = {i: 'bench_f_{}'.format(0) for i in range(num_app)}
        cur_num_fs_wk_list = [1]
    else:
        per_app_fname = {i: 'bench_f_{}'.format(i) for i in range(num_app)}

    if cur_is_cached:
        print("not used in Oxbow")
        sys.exit(1)
    else:
        cur_is_no_overlap = True
        mte_rd.bench_rand_read(
            cur_log_dir,
            num_app_proc=num_app,
            is_fsp=cur_is_fsp,
            is_oxbow=cur_is_oxbow,
            is_thp=cur_is_throughput,
            is_share=cur_is_share,
            strict_no_overlap=cur_is_no_overlap,
            per_app_fname=per_app_fname,
            dump_iostat=cur_dump_io_stat,
            num_fsp_worker_list=cur_num_fs_wk_list)

    os.mkdir(CUR_ARKV_DIR)
    os.system("mv {}/log{}* {}".format(BASE_DIR, tc.get_year_str(), CUR_ARKV_DIR))
    # save the mount option for the device to check the kernel FS experiment
    # config

    # if not cur_is_fsp:
    #     os.system("tune2fs -l /dev/{} > {}/kfs_mount_option".format(
    #         cur_dev_name, CUR_ARKV_DIR))
    #     tc.dump_kernel_dirty_flush_config(CUR_ARKV_DIR)

    time.sleep(1)

tc.save_default_cfg_config(CUR_ARKV_DIR)
