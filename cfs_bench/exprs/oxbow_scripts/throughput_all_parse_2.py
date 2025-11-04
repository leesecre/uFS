import argparse
import csv
import os
import pprint
import re
from collections import defaultdict
from pathlib import Path

# Execute relative to the working directory
BASE_DIR = Path('.')

# Map directory name to operation name
dir_to_op = {
    'ADPS': 'append',
    'WDPS': 'sequential write',
    'WDPR': 'random write',
    'RDPS': 'sequential read',
    'RDPR': 'random read',
}

op_order = ['append', 'sequential write', 'random write', 'sequential read', 'random read']

# {(syncop, operation, io_size_KB, process_count) : total_throughput_MBps}
throughput_results = defaultdict(float)
# {(syncop, operation, io_size_KB, process_count) : number_of_records_added}
throughput_counts = defaultdict(int)
fsync_results = defaultdict(list)

def parse_throughput_from_log(filepath, syncop, operation, process_count, iosize):
    tput_found = False

    io_size = int(iosize) // 1024  # KB

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if "MB/s" in line and "micros/op" in line:
            match = re.search(r"([\d.]+)\s+MB/s", line)
            if match:
                mbps = float(match.group(1))
                key = (syncop, operation, io_size, process_count)
                throughput_results[key] += mbps
                throughput_counts[key] += 1
                tput_found = True

    if not tput_found:
        print(f"No throughput result was found in {filepath}")

def parse_fsync_time_from_log(filepath, syncop, operation, process_count, iosize):
    in_fsync_block = False
    io_size = int(iosize) // 1024  # in KB

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if "Microseconds per fsync" in line:
            in_fsync_block = True
            continue

        if in_fsync_block and "Average:" in line:
            match = re.search(r"Average:\s+([\d.]+)", line)
            if match:
                avg_us = float(match.group(1))
                avg_ms = avg_us / 1000.0  # convert to milliseconds
                key = (syncop, operation, io_size, process_count)
                fsync_results[key].append(avg_ms)
            in_fsync_block = False

def find_and_parse_write_logs(system_name):
    subdirs = []
    pattern = f'{system_name}_*_run_0'
    for subdir in BASE_DIR.rglob(pattern):
        match_dir = re.search(fr'{re.escape(system_name)}_(ADPS|WDPS|WDPR)_run_0', str(subdir))
        if not match_dir:
            # print(f"Skipping {subdir} as it does not match expected pattern.")
            continue

        # print(f"Parsing write logs in {subdir}.")
        op_key = match_dir.group(1)
        subdirs.append((op_key, subdir))

    # Sort by operation order
    subdirs.sort(key=lambda x: op_order.index(dir_to_op.get(x[0], '')))

    for op_key, subdir in subdirs:
        operation = dir_to_op.get(op_key)
        if not operation:
            continue

        app_dirs = []
        log_pattern = f'log_{system_name}_*_syncop_*_throughput*'
        for app_dir in subdir.glob(log_pattern):
            match_proc = re.search(r'app_(\d+)', app_dir.name)
            match_syncop = re.search(r'syncop_(-?\d+)', app_dir.name)
            if not match_proc or not match_syncop:
                continue
            process_count = int(match_proc.group(1))
            syncop = int(match_syncop.group(1))
            app_dirs.append((syncop, process_count, app_dir))

        # Sort by (syncop, process)
        app_dirs.sort()

        # print(app_dirs)

        for syncop, process_count, app_dir in app_dirs:
            for log_file in app_dir.rglob('bench_log_*'):
                if not log_file.is_file():
                    continue

                # Parse iosize from log file name.
                match_iosize = re.search(r'_iosize(\d+)', log_file.name)
                if not match_iosize:
                    print(f"Skipping {log_file} as it does not match expected iosize pattern.")
                    continue
                iosize = int(match_iosize.group(1))

                parse_throughput_from_log(log_file, syncop, operation, process_count, iosize)
                parse_fsync_time_from_log(log_file, syncop, operation, process_count, iosize)

def find_and_parse_read_logs(system_name):
    subdirs = []
    pattern = f'{system_name}_*_run_0'
    for subdir in BASE_DIR.rglob(pattern):
        match_dir = re.search(fr'{re.escape(system_name)}_(RDPS|RDPR)_run_0', str(subdir))
        if not match_dir:
            # print(f"Skipping {subdir} as it does not match expected pattern.")
            continue

        # print(f"Parsing read logs in {subdir}.")
        op_key = match_dir.group(1)
        subdirs.append((op_key, subdir))

    # Sort by operation order
    subdirs.sort(key=lambda x: op_order.index(dir_to_op.get(x[0], '')))

    for op_key, subdir in subdirs:
        operation = dir_to_op.get(op_key)
        if not operation:
            continue

        app_dirs = []
        log_pattern = f'log_{system_name}_*_throughput*'
        for app_dir in subdir.glob(log_pattern):
            match_proc = re.search(r'app_(\d+)', app_dir.name)
            if not match_proc:
                continue
            process_count = int(match_proc.group(1))
            syncop = 0 # Not used in read benchmarks.
            app_dirs.append((syncop, process_count, app_dir))

        # Sort by (syncop, process)
        app_dirs.sort()

        for syncop, process_count, app_dir in app_dirs:
            for log_file in app_dir.rglob('bench_log_*'):
                if not log_file.is_file():
                    continue

                # Parse iosize from log file name.
                match_iosize = re.search(r'_iosize(\d+)', log_file.name)
                if not match_iosize:
                    print(f"Skipping {log_file} as it does not match expected iosize pattern.")
                    continue
                iosize = int(match_iosize.group(1))

                parse_throughput_from_log(log_file, syncop, operation, process_count, iosize)

def verify_throughput_counts():
    mismatches = []
    for (syncop, operation, io_size, process_count), _ in throughput_results.items():
        observed_count = throughput_counts[(syncop, operation, io_size, process_count)]
        if observed_count != process_count:
            mismatches.append((syncop, operation, io_size, process_count, observed_count))

    if mismatches:
        print("Removing entries with count mismatch:")
        for syncop, operation, io_size, process_count, observed_count in mismatches:
            key = (syncop, operation, io_size, process_count)
            print(
                f"  removing: syncop={syncop}, op={operation}, iosize={io_size}K, "
                f"process_count={process_count}, observed_count={observed_count}"
            )
            throughput_results.pop(key, None)
            throughput_counts.pop(key, None)

def write_throughput_csv(system_name):
    filename = f'{system_name}_micro_tput_results.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "syncop",
                "operation",
                "io size (K)",
                "process",
                "total throughput (MB/s)",
                "avg fsync (ms)",
                "min fsync (ms)",
                "max fsync (ms)",
            ]
        )

        sorted_keys = sorted(
            throughput_results.keys(),
            key=lambda x: (x[0], op_order.index(x[1]), x[2], x[3])
        )

        # pprint.pprint(fsync_results)

        for (syncop, operation, io_size, process_count) in sorted_keys:
            fsync_min = None
            fsync_max = None
            fsync_avg = None

            if operation == 'sequential write' or operation == 'random write' or operation == 'append':
                fsync_values = fsync_results[(syncop, operation, io_size, process_count)]
                # print(f"fsync_values: {fsync_values} keys: {syncop, operation, io_size, process_count}")
                fsync_avg = sum(fsync_values) / len(fsync_values)
                fsync_avg = round(fsync_avg, 4)
                fsync_min = round(min(fsync_values), 4)
                fsync_max = round(max(fsync_values), 4)

            writer.writerow(
                [
                    syncop,
                    operation,
                    f"{io_size}K",
                    process_count,
                    throughput_results[(syncop, operation, io_size, process_count)],
                    fsync_avg,
                    fsync_min,
                    fsync_max,
                ]
            )
    print(f"Throughput result is saved to {filename}.")
    os.system(f"cat {filename}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse throughput results from benchmark logs')
    parser.add_argument('--system', '-s', required=True, choices=['oxbow', 'ext4'],
                        help='System name (oxbow or ext4)')
    args = parser.parse_args()

    find_and_parse_write_logs(args.system)
    find_and_parse_read_logs(args.system)
    verify_throughput_counts()
    write_throughput_csv(args.system)
