import csv
import os
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

def parse_throughput_from_log(filepath, syncop, operation, process_count):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    io_size = None

    for line in lines:
        if line.startswith("Values:"):
            match = re.search(r"Values:\s+(\d+) bytes", line)
            if match:
                io_size = int(match.group(1)) // 1024  # KB

        if "MB/s" in line and "micros/op" in line:
            match = re.search(r"([\d.]+)\s+MB/s", line)
            if match and io_size is not None:
                mbps = float(match.group(1))
                key = (syncop, operation, io_size, process_count)
                throughput_results[key] += mbps

def find_and_parse_all_logs():
    subdirs = []
    for subdir in BASE_DIR.rglob('oxbow_*_run_0'):
        match_dir = re.search(r'oxbow_(ADPS|WDPS|WDPR|RDPS|RDPR)_run_0', str(subdir))
        if not match_dir:
            print(f"Skipping {subdir} as it does not match expected pattern.")
            continue

        op_key = match_dir.group(1)
        subdirs.append((op_key, subdir))

    # Sort by operation order
    subdirs.sort(key=lambda x: op_order.index(dir_to_op.get(x[0], '')))

    for op_key, subdir in subdirs:
        operation = dir_to_op.get(op_key)
        if not operation:
            continue

        app_dirs = []
        for app_dir in subdir.glob('log_oxbow_*_syncop_*_throughput*'):
            match_proc = re.search(r'app_(\d+)', app_dir.name)
            match_syncop = re.search(r'syncop_(-?\d+)', app_dir.name)
            if not match_proc or not match_syncop:
                continue
            process_count = int(match_proc.group(1))
            syncop = int(match_syncop.group(1))
            app_dirs.append((syncop, process_count, app_dir))

        # Sort by (syncop, process)
        app_dirs.sort()

        for syncop, process_count, app_dir in app_dirs:
            for log_file in app_dir.rglob('bench_log_*'):
                if log_file.is_file():
                    parse_throughput_from_log(log_file, syncop, operation, process_count)

def write_throughput_csv(filename='ufs_micro_tput_results.csv'):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["syncop", "operation", "io size (K)", "process", "total throughput (MB/s)"])

        sorted_keys = sorted(
            throughput_results.keys(),
            key=lambda x: (x[0], op_order.index(x[1]), x[2], x[3])
        )

        for (syncop, operation, io_size, process_count) in sorted_keys:
            writer.writerow([
                syncop,
                operation,
                f"{io_size}K",
                process_count,
                throughput_results[(syncop, operation, io_size, process_count)]
            ])

if __name__ == '__main__':
    find_and_parse_all_logs()
    write_throughput_csv()
