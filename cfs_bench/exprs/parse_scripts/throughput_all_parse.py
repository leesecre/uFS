import os
import re
import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path('.')

# 디렉토리명 → operation 이름 매핑
dir_to_op = {
    'RDPR': 'random read',
    'RDPS': 'sequential read',
    'ADPS': 'append',
    # 필요한 경우 더 추가 가능
}

# {(operation, io_size_KB, process_count) : total_throughput_MBps}
throughput_results = defaultdict(float)

def parse_throughput_from_log(filepath, operation, process_count):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    io_size = None

    for line in lines:
        if line.startswith("Values:"):
            match = re.search(r"Values:\s+(\d+) bytes", line)
            if match:
                io_size = int(match.group(1)) // 1024  # KB

        if "MB/s" in line:
            match = re.search(r"([\d.]+)\s+MB/s", line)
            if match and io_size is not None:
                mbps = float(match.group(1))
                key = (operation, io_size, process_count)
                throughput_results[key] += mbps

def find_and_parse_all_logs():
    for subdir in BASE_DIR.rglob('fsp_*_run_0'):
        match_dir = re.search(r'fsp_(RDPR|RDPS|ADPS)_run_0', str(subdir))
        if not match_dir:
            continue

        op_key = match_dir.group(1)
        operation = dir_to_op.get(op_key)

        for app_dir in subdir.glob('log_fsp_*_app_*'):
            match_app = re.search(r'app_(\d+)', app_dir.name)
            if not match_app:
                continue
            process_count = int(match_app.group(1))

            for log_file in app_dir.rglob('bench_log_*'):
                if log_file.is_file():
                    parse_throughput_from_log(log_file, operation, process_count)

def write_throughput_csv(filename='throughput_results.csv'):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["operation", "io size (K)", "process", "total throughput (MB/s)"])
        for (operation, io_size, process_count) in sorted(throughput_results.keys()):
            writer.writerow([
                operation,
                f"{io_size}K",
                process_count,
                throughput_results[(operation, io_size, process_count)]
            ])

if __name__ == '__main__':
    find_and_parse_all_logs()
    write_throughput_csv()
