import os
import re
import csv
from pathlib import Path

# 작업 디렉토리 기준으로 실행
BASE_DIR = Path('.')

# operation 이름 매핑
operation_order = ["append", "sequential write", "random write", "sequential read", "random read"]
dir_to_op = {
    'ADPS': 'append',
    'WDPS': 'sequential write',
    'WDPR': 'random write',
    'RDPS': 'sequential read',
    'RDPR': 'random read'
}

# 결과 저장용 리스트
results = []

# bench_log_0 파싱 함수
def parse_bench_log(filepath, operation):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    io_size = None
    op_stats = {}
    fsync_stats = {}
    in_op = False
    in_fsync = False

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("Values:"):
            match = re.search(r"Values:\s+(\d+) bytes", line)
            if match:
                if io_size and op_stats:
                    row = [operation, f"{io_size // 1024}K",
                           op_stats.get('average'), op_stats.get('stddev'),
                           op_stats.get('min'), op_stats.get('median'), op_stats.get('max')]
                    if 'read' in operation:
                        row += [None] * 5
                    else:
                        row += [
                            fsync_stats.get('average'),
                            fsync_stats.get('stddev'),
                            fsync_stats.get('min'),
                            fsync_stats.get('median'),
                            fsync_stats.get('max')
                        ]
                    results.append(row)
                io_size = int(match.group(1))
                op_stats = {}
                fsync_stats = {}

        if line.startswith("Microseconds per op:"):
            in_op = True
            in_fsync = False

        elif line.startswith("Microseconds per fsync:"):
            in_fsync = True
            in_op = False

        elif in_op or in_fsync:
            stats_line = line.strip()
            match = re.findall(r"(Count|Average|StdDev|Min|Median|Max):\s*([\d.]+)", stats_line)
            for key, val in match:
                if in_op:
                    op_stats[key.lower()] = float(val)
                elif in_fsync:
                    fsync_stats[key.lower()] = float(val)

        i += 1

    # 마지막 블록 처리
    if io_size and op_stats:
        row = [operation, f"{io_size // 1024}K",
               op_stats.get('average'), op_stats.get('stddev'),
               op_stats.get('min'), op_stats.get('median'), op_stats.get('max')]
        if 'read' in operation:
            row += [None] * 5
        else:
            row += [
                fsync_stats.get('average'),
                fsync_stats.get('stddev'),
                fsync_stats.get('min'),
                fsync_stats.get('median'),
                fsync_stats.get('max')
            ]
        results.append(row)

# 디렉토리 순회
def find_and_parse_logs():
    for subdir in BASE_DIR.rglob('fsp_*_run_0'):
        match = re.search(r'fsp_(ADPS|RDPR|RDPS|WDPR|WDPS)_run_0', str(subdir))
        if match:
            key = match.group(1)
            operation = dir_to_op[key]
            for log_file in subdir.rglob('bench_log_0'):
                if log_file.is_file():
                    parse_bench_log(log_file, operation)

# CSV 저장 함수
def write_csv(filename='results.csv'):
    header = ["operation", "io size (K)", "average", "stddev", "min", "median", "max",
              "fsync average", "fsync stddev", "fsync min", "fsync median", "fsync max"]
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for op in operation_order:
            for row in results:
                if row[0] == op:
                    writer.writerow(row)

if __name__ == '__main__':
    find_and_parse_logs()
    write_csv()