import os
import re
import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path('.')

dir_to_op = {
    'ADPS': 'append',
    'WDPS': 'sequential write',
    'WDPR': 'random write',
    'RDPS': 'sequential read',
    'RDPR': 'random read',
}

op_order = ['append', 'sequential write', 'random write', 'sequential read', 'random read']

# (fs, syncop, operation, io_size_KB, process_count): list of avg_fsync (in ms)
fsync_results = defaultdict(list)

def parse_log_file(filepath, filesystem, syncop, operation, process_count):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    io_size = None
    in_fsync_block = False

    for line in lines:
        if line.startswith("Values:"):
            match = re.search(r"Values:\s+(\d+) bytes", line)
            if match:
                io_size = int(match.group(1)) // 1024  # in KB

        if "Microseconds per fsync" in line:
            in_fsync_block = True
            continue

        if in_fsync_block and "Average:" in line:
            match = re.search(r"Average:\s+([\d.]+)", line)
            if match and io_size is not None:
                avg_us = float(match.group(1))
                avg_ms = avg_us / 1000.0  # convert to milliseconds
                key = (filesystem, syncop, operation, io_size, process_count)
                fsync_results[key].append(avg_ms)
            in_fsync_block = False

def find_and_parse_all_logs():
    subdirs = []
    for subdir in BASE_DIR.rglob('*_*_run_0'):
        match_dir = re.search(r'([^_/]+)_(ADPS|WDPS|WDPR|RDPS|RDPR)_run_0', str(subdir))
        if not match_dir:
            continue
        filesystem = match_dir.group(1)
        op_key = match_dir.group(2)
        subdirs.append((filesystem, op_key, subdir))

    subdirs.sort(key=lambda x: op_order.index(dir_to_op.get(x[1], '')))

    for filesystem, op_key, subdir in subdirs:
        operation = dir_to_op.get(op_key)
        if not operation:
            continue

        app_dirs = []
        for app_dir in subdir.glob('log_*_syncop_*_throughput*'):
            match_proc = re.search(r'app_(\d+)', app_dir.name)
            match_syncop = re.search(r'syncop_(-?\d+)', app_dir.name)
            if not match_proc or not match_syncop:
                continue
            process_count = int(match_proc.group(1))
            syncop = int(match_syncop.group(1))
            app_dirs.append((syncop, process_count, app_dir))

        app_dirs.sort()

        for syncop, process_count, app_dir in app_dirs:
            for log_file in app_dir.rglob('bench_log_*'):
                if log_file.is_file():
                    parse_log_file(log_file, filesystem, syncop, operation, process_count)

def write_fsync_csv(filename='fsync_results.csv'):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["filesystem", "syncop", "operation", "io size (K)", "process", "avg fsync (ms)", "min fsync (ms)", "max fsync (ms)"])

        sorted_keys = sorted(
            fsync_results.keys(),
            key=lambda x: (x[0], x[1], op_order.index(x[2]), x[3], x[4])
        )

        for (filesystem, syncop, operation, io_size, process_count) in sorted_keys:
            values = fsync_results[(filesystem, syncop, operation, io_size, process_count)]
            avg = sum(values) / len(values)
            writer.writerow([
                filesystem,
                syncop,
                operation,
                f"{io_size}K",
                process_count,
                round(avg, 4),
                round(min(values), 4),
                round(max(values), 4)
            ])

if __name__ == '__main__':
    find_and_parse_all_logs()
    write_fsync_csv()