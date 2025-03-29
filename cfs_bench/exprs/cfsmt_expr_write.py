#!/usr/bin/env python3
# encoding: utf-8

import sys
import os
import time

import cfs_test_common as cfs_tc
import cfsmt_expr_read as me_read


# This assume files are initialized already is is_append is False (by default)
# benchmark pre-allocated write (i.e., no block allocation)
def bench_seq_write(
        log_dir,
        num_app_proc=1,
        is_fsp=True,
        is_append=False,
        is_share=False,
        num_fsp_worker_list=None,
        per_app_fname=None,
        dump_mpstat=False,
        dump_iostat=False,
        cfs_update_dict=None):
    case_name = 'seqwrite'
    case_log_dir = '{}/{}'.format(log_dir, case_name)
    bench_cfg_dict = {
        '--benchmarks=': 'seqwrite',
    }

    if cfs_update_dict is not None:
        bench_cfg_dict.update(cfs_update_dict)

    value_sz_op_num_dict = {
        # 4096: int(2*1024*1024/4), # 2GB
        # 16384: int(2*1024*1024/16),
        # 32768: int(2*1024*1024/32),
        # 65536: int(2*1024*1024/64),
        
        # # 5GB for throughput benchmark
        1024: 262144 * 4 * 5, # 1K
        4096: 65536 * 4 * 5,  # 4K
        16384: 16384 * 4 * 5, # 16K
        65536: 4096 * 4 * 5, # 64K
        262144: 1024 * 4 * 5, # 256K
        524288: 512 * 4 * 5, # 512K
        # # 1048576: 256 * 4 * 5, # 1M
        # # 2097152: 128 * 4 * 5 # 2M
        
        # multi process test
        # 4096: int(2*1024*1024/4),
        # 16384: int(2*1024*1024/16),
        # 65536: int(2*1024*1024/64),
        # 262144: int(2*1024*1024/256),
    }
    # num_op_limit_dict = {
    #     # 4096: 400000, #2G
    #     # 4096: 1000000,  # 8G
    #     # 4096: 500000, #8G
    #     # 16384: 200000,
    #     # 65536: 
    #     # 1073741824: 

    #     # 5GB for throughput benchmark
    #     # 1024: 262144 * 4 * 5, # 1K
    #     # 4096: 65536 * 4 * 5,  # 4K
    #     # 16384: 16384 * 4 * 5, # 16K
    #     # 65536: 4096 * 4 * 5, # 64K
    #     # 262144: 1024 * 4 * 5, # 256K
    #     # 524288: 512 * 4 * 5, # 512K
    #     # 1048576: 256 * 4 * 5, # 1M
    #     # 2097152: 128 * 4 * 5 # 2M
        
    #     # multi process test
    #     4096: int(2*1024*1024/4),
    #     16384: int(2*1024*1024/16),
    #     65536: int(2*1024*1024/64),
    #     262144: int(2*1024*1024/256),
    # }
    if is_share and len(value_sz_op_num_dict.keys()) > 0:
        # we only do expr for 4K in share case
        keys = list(value_sz_op_num_dict.keys())
        keys.remove(4096)
        for k in keys:
            del(value_sz_op_num_dict[k])

    pin_cpu_list = [True, False]
    clear_pc_list = [True]
    if num_fsp_worker_list is None:
        num_fsp_worker_list = [3]
    for cp in clear_pc_list:
        for pc in pin_cpu_list:
            for vs, nop in value_sz_op_num_dict.items():
                for nfswk in num_fsp_worker_list:
                    cur_run_log_dir = \
                        '{}_isFsp-{}_clearPc-{}_pinCpu-{}-numFsWk-{}'.format(
                            case_log_dir, str(is_fsp), str(cp), str(pc),
                            str(nfswk))
                    bench_cfg_dict['--value_size='] = vs
                    bench_cfg_dict['--numop='] = nop
                    # if nop * num_app_proc > num_op_limit_dict[vs]:
                    #     bench_cfg_dict['--numop='] = int(
                    #         num_op_limit_dict[vs] / num_app_proc)
                    # else:

                    cfs_tc.mk_accessible_dir(cur_run_log_dir)
                    if is_append:
                        # mkfs
                        if is_fsp:
                            cfs_tc.expr_mkfs()
                        else:
                            cfs_tc.expr_mkfs_for_kfs()
                        # wait a bit after mkfs
                        time.sleep(1)
                    me_read.expr_read_mtfsp_multiapp(
                        cur_run_log_dir,
                        nfswk,
                        num_app_proc,
                        bench_cfg_dict,
                        is_fsp=is_fsp,
                        clear_pgcache=cp,
                        pin_cpu=pc,
                        per_app_fname=per_app_fname,
                        dump_mpstat=dump_mpstat,
                        dump_iostat=dump_iostat)
                    time.sleep(1)


def bench_seq_sync_write(log_dir, num_app_proc=1, is_fsp=True, is_oxbow=False,
                         is_append=False,
                         num_fsp_worker_list=None, per_app_fname=None,
                         dump_mpstat=False, dump_iostat=False,
                         cfs_update_dict=None):
    case_name = 'seqwrite'
    case_log_dir = '{}/{}'.format(log_dir, case_name)
    bench_cfg_dict = {
        '--benchmarks=': 'seqwrite',
    }

    if cfs_update_dict is not None:
        bench_cfg_dict.update(cfs_update_dict)
        
    if cfs_update_dict['--sync_numop='] == 1:
        
        value_sz_op_num_dict = {
            # 256MB for latency benchmark
            # 1024: 262144, # 1K
            # 4096: 65536,  # 4K
            # 16384: 16384, # 16K
            # 65536: 4096, # 64K
            # 262144: 1024, # 256K
            # 524288: 512, # 512K

            # 1GB for latency
            1024: 262144 * 4, # 1K
            4096: 65536 * 4,  # 4K
            16384: 16384 * 4, # 16K
            65536: 4096 * 4, # 64K
            262144: 1024 * 4, # 256K
            524288: 512 * 4, # 512K
        }
    else:
        # Throughput benchmark
        value_sz_op_num_dict = {
            # 4096: 250000, # first value
            4096: 65536 * 8, # 2GB
            # 16384: 60000, # Not work
        }

    # 5GB for throughput benchmark
    # 1024: 262144 * 4 * 5, # 1K
    # 4096: 65536 * 4 * 5,  # 4K
    # 16384: 16384 * 4 * 5, # 16K
    # 65536: 4096 * 4 * 5, # 64K
    # 2097152: 128 * 4 * 5 # 2M


    if '--share_mode=' in cfs_update_dict and '--o_append=' in cfs_update_dict:
        MAX_FSIZE = 5*1024*1024*1024
        PER_APP_SIZE = MAX_FSIZE / num_app_proc
        for vsz in value_sz_op_num_dict:
            value_sz_op_num_dict[vsz] = int(PER_APP_SIZE/vsz)
    # pin_cpu_list = [True, False]
    pin_cpu_list = [True] # pinning was faster
    clear_pc_list = [True]
    if num_fsp_worker_list is None:
        num_fsp_worker_list = [3]
    for cp in clear_pc_list:
        for pc in pin_cpu_list:
            for vs, nop in value_sz_op_num_dict.items():
                for nfswk in num_fsp_worker_list:
                    cur_run_log_dir = \
                        '{}_isFsp-{}_clearPc-{}_pinCpu-{}-numFsWk-{}'.format(
                            case_log_dir, str(is_fsp), str(cp), str(pc),
                            str(nfswk))
                    bench_cfg_dict['--value_size='] = vs
                    bench_cfg_dict['--numop='] = nop
                    cfs_tc.mk_accessible_dir(cur_run_log_dir)
                    if is_append:
                        # mkfs
                        if is_fsp:
                            cfs_tc.expr_mkfs()
                        elif is_oxbow:
                            cfs_tc.expr_mkfs_oxbow()
                        else:
                            cfs_tc.expr_mkfs_for_kfs()
                        # wait a bit after mkfs
                        time.sleep(1)
                    me_read.expr_read_mtfsp_multiapp(
                        cur_run_log_dir,
                        nfswk,
                        num_app_proc,
                        bench_cfg_dict,
                        is_fsp=is_fsp,
                        is_oxbow=is_oxbow,
                        is_append=is_append,
                        clear_pgcache=cp,
                        pin_cpu=pc,
                        per_app_fname=per_app_fname,
                        dump_mpstat=dump_mpstat,
                        dump_iostat=dump_iostat)
                    time.sleep(1)


def bench_rand_write(log_dir, num_app_proc=1, is_fsp=True, is_oxbow=False,
                     is_append=False, is_cached=True,
                     num_fsp_worker_list=None, per_app_fname=None,
                     dump_mpstat=False, dump_iostat=False,
                     cfs_update_dict=None):
    # note currently only support random write for buffered workload
    # assert(is_cached)

    case_name = 'rwrite'
    case_log_dir = '{}/{}'.format(log_dir, case_name)
    bench_cfg_dict = {
        '--benchmarks=': 'rwrite',
        # random write to a 1M range
        # '--max_file_size=': (1024 * 1024),
    }

    # if not is_cached:
    #     bench_cfg_dict['--max_file_size='] = 2 * 1024 * 1024 * 1024
    #     # make the on-disk write aligned (avoid read traffic)
    #     bench_cfg_dict['--rw_align_bytes='] = 4096

    if cfs_update_dict is not None:
        bench_cfg_dict.update(cfs_update_dict)

    if is_cached:
        value_sz_op_num_dict = {
            # 64: 1000000,
            # 1024: 200000,
            4096: 1000000,
            # 16384: 1000000,
        }
    else:
        if cfs_update_dict['--sync_numop='] == 1:
            value_sz_op_num_dict = {
                # 256MB for latency benchmark
                # 1024: 262144, # 1K
                # 4096: 65536,  # 4K
                # 16384: 16384, # 16K
                # 65536: 4096, # 64K
                # 262144: 1024, # 256K
                # 524288: 512, # 512K
                
                # 1GB for latency
                1024: 262144 * 4, # 1K
                4096: 65536 * 4,  # 4K
                16384: 16384 * 4, # 16K
                65536: 4096 * 4, # 64K
                262144: 1024 * 4, # 256K
                524288: 512 * 4, # 512K
            }
        else:
            # Throughput benchmark
            value_sz_op_num_dict = {
                # 4096: 250000, # first value
                4096: 65536 * 8,  # 2G
                #16384: 60000, # Not work
            }

    # pin_cpu_list = [True, False]
    pin_cpu_list = [True, False]
    clear_pc_list = [True]
    if num_fsp_worker_list is None:
        num_fsp_worker_list = [1]
    for cp in clear_pc_list:
        for pc in pin_cpu_list:
            for vs, nop in value_sz_op_num_dict.items():    
                for nfswk in num_fsp_worker_list:
                    cur_run_log_dir = \
                        '{}_isFsp-{}_clearPc-{}_pinCpu-{}-numFsWk-{}'.format(
                            case_log_dir, str(is_fsp), str(cp), str(pc),
                            str(nfswk))
                    bench_cfg_dict['--value_size='] = vs
                    bench_cfg_dict['--numop='] = nop
                    cfs_tc.mk_accessible_dir(cur_run_log_dir)
                    if is_append:
                        # mkfs
                        if is_fsp:
                            cfs_tc.expr_mkfs()
                        elif is_oxbow:
                            cfs_tc.expr_mkfs_oxbow()
                        else:
                            cfs_tc.expr_mkfs_for_kfs()
                        # wait a bit after mkfs
                        time.sleep(1)
                    me_read.expr_read_mtfsp_multiapp(
                        cur_run_log_dir,
                        nfswk,
                        num_app_proc,
                        bench_cfg_dict,
                        is_fsp=is_fsp,
                        is_oxbow=is_oxbow,
                        clear_pgcache=cp,
                        pin_cpu=pc,
                        per_app_fname=per_app_fname,
                        dump_mpstat=dump_mpstat,
                        dump_iostat=dump_iostat)
                    time.sleep(1)


def bench_cwcross(log_dir, num_app_proc=1, is_fsp=True,
                  is_append=False, is_cached=True,
                  num_fsp_worker_list=None, per_app_block_no=None,
                  dump_mpstat=False, dump_iostat=False,
                  cfs_update_dict=None):
    # note currently only support random write for buffered workload
    assert(is_cached)

    case_name = 'cwcross'
    case_log_dir = '{}/{}'.format(log_dir, case_name)
    bench_cfg_dict = {
        '--benchmarks=': 'crwritecross',
    }

    if cfs_update_dict is not None:
        bench_cfg_dict.update(cfs_update_dict)

    value_sz_op_num_dict = {
        # 4096: 1000000,
        # 4096: 1000000,
        2: 1000000,
    }
    # pin_cpu_list = [True, False]
    pin_cpu_list = [True]
    clear_pc_list = [True]
    if num_fsp_worker_list is None:
        num_fsp_worker_list = [1]
    for cp in clear_pc_list:
        for pc in pin_cpu_list:
            for vs, nop in value_sz_op_num_dict.items():
                for nfswk in num_fsp_worker_list:
                    cur_run_log_dir = \
                        '{}_isFsp-{}_clearPc-{}_pinCpu-{}-numFsWk-{}'.format(
                            case_log_dir, str(is_fsp), str(cp), str(pc),
                            str(nfswk))
                    bench_cfg_dict['--value_size='] = vs
                    bench_cfg_dict['--numop='] = nop
                    cfs_tc.mk_accessible_dir(cur_run_log_dir)
                    if is_append:
                        # mkfs
                        if is_fsp:
                            cfs_tc.expr_mkfs()
                        else:
                            cfs_tc.expr_mkfs_for_kfs()
                        # wait a bit after mkfs
                        time.sleep(1)
                    me_read.expr_read_mtfsp_multiapp(
                        cur_run_log_dir,
                        nfswk,
                        num_app_proc,
                        bench_cfg_dict,
                        is_fsp=is_fsp,
                        clear_pgcache=cp,
                        pin_cpu=pc,
                        per_app_block_no=per_app_block_no,
                        dump_mpstat=dump_mpstat,
                        dump_iostat=dump_iostat)
                    time.sleep(1)


def main():
    # fsp
    # cur_log_dir = cfs_tc.get_proj_log_dir(cfs_tc.get_expr_user(),
    #                                       suffix=cfs_tc.get_ts_dir_name(),
    #                                       do_mkdir=True)
    # bench_seq_write(cur_log_dir, num_app_proc=5, is_fsp=True)
    # ext4
    # cur_log_dir = cfs_tc.get_proj_log_dir(cfs_tc.get_expr_user(),
    #                                       suffix=cfs_tc.get_ts_dir_name(),
    #                                       do_mkdir=True)
    # bench_seq_write(cur_log_dir, num_app_proc=3, is_fsp=False,
    #                 dump_mpstat=True, dump_iostat=True)
    pass


if __name__ == '__main__':
    is_root = cfs_tc.check_root()
    if not is_root:
        print('Run as root required!')
        exit(1)
    main()
