#!/usr/bin/env python3
# encoding: utf-8

import sys
import os
import time

import cfsmt_expr_read as mte_rd
import cfs_test_common as tc


def print_usage():
    print(
        'Usage: {} <ext4 | fsp> [cached] [share] [mpstat] [blk=N] [numapp=]'.format(
            sys.argv[0]))


if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

cur_is_fsp = None
if 'ext4' in sys.argv[1]:
    cur_is_fsp = False
    cur_dev_name = tc.get_kfs_dev_name()
elif 'fsp' in sys.argv[1]:
    cur_is_fsp = True
else:
    print_usage()
    sys.exit(1)
print('is_fsp? - {}'.format(str(cur_is_fsp)))


cur_is_cached = False
cur_is_no_overlap = True
cur_is_dump_mpstat = False
cur_block_no = -1
cur_is_share = False
cur_numapp = None


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


print('is_cached? - {}'.format(str(cur_is_cached)))
print('is_dump_mpstat? - {}'.format(str(cur_is_dump_mpstat)))
print('block_no - {}'.format(cur_block_no))
print('is_share_file? - {}'.format(str(cur_is_share)))

# Once block number is fixed, it is definitely a cached workload
if cur_block_no >= 0:
    assert(cur_is_cached)


LOG_BASE = 'log_{}'.format(sys.argv[1])

# num_app_list = [1, 2, 3, 4, 5, 6]  # @falcon
# num_app_list = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]  # @bumble
#num_app_list = [20 - i for i in range(20)]

num_app_list = [1,2,4,8,10] # for multi process test
# num_app_list = [1]
# if cur_numapp is not None:
#     num_app_list = list(range(1, cur_numapp + 1))
#     num_app_list.reverse()

# if tc.use_exact_num_app():
#     num_app_list = [cur_numapp]

for num_app in num_app_list:
    # cur_num_fs_wk_list = [(i + 1) for i in range(num_app)]
    if not cur_is_fsp:
        print("not cur is fsp")
        cur_num_fs_wk_list = [1]
    else:
        cur_num_fs_wk_list = [num_app]
        pass
    # if tc.use_single_worker():
    #     cur_num_fs_wk_list = [1]
    print(cur_num_fs_wk_list)
    cur_log_dir = tc.get_proj_log_dir(tc.get_expr_user(),
                                      suffix=tc.get_ts_dir_name(),
                                      do_mkdir=True)
    # dump io stats for kernel fs
    cur_dump_io_stat = False
    if not cur_is_fsp:
        cur_dump_io_stat = True

    # stress sharing
    if cur_is_share:
        per_app_fname = {i: 'bench_f_{}'.format(0) for i in range(num_app)}
        cur_num_fs_wk_list = [1]
    else:
        per_app_fname = {i: 'bench_f_{}'.format(i) for i in range(num_app)}
    
    # per_app_fname = 'bench_f_{}'.format(str(num_app))
    print(per_app_fname)

    if cur_is_cached:
        # buffered seq read
        CUR_ARKV_DIR = '{}_csread_app_{}'.format(LOG_BASE, num_app)
        mte_rd.bench_cached_read(
            cur_log_dir,
            num_app_proc=num_app,
            is_fsp=cur_is_fsp,
            is_seq=True,
            block_no=cur_block_no,
            per_app_fname=per_app_fname,
            dump_mpstat=cur_is_dump_mpstat,
            cfs_update_dict={'--in_mem_file_size=': int(64 * 1024)},
            num_fsp_worker_list=cur_num_fs_wk_list)
    else:
        # on-disk sequtial read
        CUR_ARKV_DIR = '{}_seqread_app_{}'.format(LOG_BASE, num_app)
        cur_is_no_overlap = True
        mte_rd.bench_rand_read(
            cur_log_dir,
            num_app_proc=num_app,
            is_fsp=cur_is_fsp,
            is_seq=True,
            strict_no_overlap=cur_is_no_overlap,
            per_app_fname=per_app_fname,
            dump_iostat=cur_dump_io_stat,
            num_fsp_worker_list=cur_num_fs_wk_list)

    os.mkdir(CUR_ARKV_DIR)
    os.system("mv log{}* {}".format(tc.get_year_str(), CUR_ARKV_DIR))
    # save the mount option for the device to check the kernel FS experiment
    # config
    if not cur_is_fsp:
        os.system("tune2fs -l /dev/{} > {}/kfs_mount_option".format(
            cur_dev_name, CUR_ARKV_DIR))
        tc.dump_kernel_dirty_flush_config(CUR_ARKV_DIR)
    time.sleep(1)

tc.save_default_cfg_config(CUR_ARKV_DIR)
