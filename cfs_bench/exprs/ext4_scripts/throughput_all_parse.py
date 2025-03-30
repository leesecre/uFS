import os
import re
import csv
from pathlib import Path
from collections import defaultdict

# 작업 디렉토리 기준으로 실행
BASE_DIR = Path('.')

# 디렉토리명 → operation 이름 매핑
dir_to_op = {
    'ADPS': 'append',
    'WDPS': 'sequential write',
    'WDPR': 'random write',
    'RDPS': 'sequential read',
    'RDPR': 'random read',
    # 필요한 경우 더 추가 가능
}

op_order = ['ADPS', 'WDPS', 'WDPR', 'RDPS', 'RDPR']

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
    subdirs = []
    for subdir in BASE_DIR.rglob('ext4_*_run_0'):
        match_dir = re.search(r'ext4_(ADPS|WDPS|WDPR|RDPS|RDPR)_run_0', str(subdir))
        if not match_dir:
            print(f"Skipping {subdir} as it does not match expected pattern.")
            continue

        op_key = match_dir.group(1)
        subdirs.append((op_key, subdir))

    # 원하는 순서대로 정렬
    subdirs.sort(key=lambda x: op_order.index(x[0]))
    
    for op_key, subdir in subdirs:
        operation = dir_to_op.get(op_key)
        if not operation:
            continue

        app_dirs = []
        for app_dir in subdir.glob('log_ext4_*_throughput*'):
            match_app = re.search(r'(\d+)$', app_dir.name)  # 디렉토리 이름 끝의 숫자
            if not match_app:
                continue
            process_count = int(match_app.group(1))
            app_dirs.append((process_count, app_dir))

        # 숫자 기준 오름차순 정렬
        app_dirs.sort(key=lambda x: x[0])

        # 로그 파일 파싱
        for process_count, app_dir in app_dirs:
            for log_file in app_dir.rglob('bench_log_*'):
                if log_file.is_file():
                    parse_throughput_from_log(log_file, operation, process_count)

def write_throughput_csv(filename='throughput_results.csv'):
    op_order = ['append', 'sequential write', 'random write', 'sequential read', 'random read']

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["operation", "io size (K)", "process", "total throughput (MB/s)"])

        # 정렬: operation → io_size → process_count 순
        sorted_keys = sorted(
            throughput_results.keys(),
            key=lambda x: (op_order.index(x[0]), x[1], x[2])  # io_size는 정수
        )

        for (operation, io_size, process_count) in sorted_keys:
            writer.writerow([
                operation,
                f"{io_size}K",
                process_count,
                throughput_results[(operation, io_size, process_count)]
            ])


if __name__ == '__main__':
    find_and_parse_all_logs()
    write_throughput_csv()
