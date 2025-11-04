import argparse
import csv
import os
import re
from pathlib import Path

# Execute relative to the working directory
BASE_DIR = Path(".")

# Operation ordering and mapping
operation_order = [
    "append",
    "sequential write",
    "random write",
    "sequential read",
    "random read",
]
dir_to_op = {
    "ADPS": "append",
    "WDPS": "sequential write",
    "WDPR": "random write",
    "RDPS": "sequential read",
    "RDPR": "random read",
}

# Container for parsed results
results = []


# Parse a single bench_log_0 file
def parse_bench_log(filepath, operation):
    with open(filepath, "r", encoding="utf-8") as f:
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
                    row = [
                        operation,
                        f"{io_size // 1024}K",
                        op_stats.get("average"),
                        op_stats.get("stddev"),
                        op_stats.get("min"),
                        op_stats.get("median"),
                        op_stats.get("max"),
                    ]
                    if "read" in operation:
                        row += [None] * 5
                    else:
                        row += [
                            fsync_stats.get("average"),
                            fsync_stats.get("stddev"),
                            fsync_stats.get("min"),
                            fsync_stats.get("median"),
                            fsync_stats.get("max"),
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
            # print(f"in_op: {in_op}, in_fsync: {in_fsync} line: {line}")
            stats_line = line.strip()
            match = re.findall(
                r"(Count|Average|StdDev|Min|Median|Max):\s*([\d.]+)", stats_line
            )
            for key, val in match:
                if in_op:
                    # print(f"in_op: {key.lower()} {val}")
                    op_stats[key.lower()] = float(val)
                elif in_fsync:
                    # print(f"in_fsync: {key.lower()} {val}")
                    fsync_stats[key.lower()] = float(val)

        i += 1
    
    # print(f"filepath: {filepath}")
    # print(f"operation: {operation}")
    # print(f"io_size: {io_size}")
    # print(f"op_stats: {op_stats}")
    # print(f"fsync_stats: {fsync_stats}\n")

    # Handle the last block
    if io_size and op_stats:
        row = [
            operation,
            f"{io_size // 1024}K",
            op_stats.get("average"),
            op_stats.get("stddev"),
            op_stats.get("min"),
            op_stats.get("median"),
            op_stats.get("max"),
        ]
        if "read" in operation:
            row += [None] * 5
        else:
            row += [
                fsync_stats.get("average"),
                fsync_stats.get("stddev"),
                fsync_stats.get("min"),
                fsync_stats.get("median"),
                fsync_stats.get("max"),
            ]
        results.append(row)


# Walk directories and parse matching logs
def find_and_parse_logs(system_name):
    pattern = f"{system_name}_*_L_run_0"
    for subdir in BASE_DIR.rglob(pattern):
        match = re.search(fr"{re.escape(system_name)}_(ADPS|RDPR|RDPS|WDPR|WDPS)_L_run_0", str(subdir))
        if match:
            key = match.group(1)
            operation = dir_to_op[key]
            for latency_dir in subdir.rglob("*_latency*"):
                if latency_dir.is_dir():
                    for log_file in latency_dir.rglob("bench_log_*_0"):
                        if log_file.is_file():
                            parse_bench_log(log_file, operation)


# Write results to CSV
def write_latency_csv(system_name):
    filename = f"{system_name}_micro_lat_results.csv"
    header = [
        "operation",
        "io size (K)",
        "average",
        "stddev",
        "min",
        "median",
        "max",
        "fsync average",
        "fsync stddev",
        "fsync min",
        "fsync median",
        "fsync max",
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for op in operation_order:
            for row in results:
                if row[0] == op:
                    writer.writerow(row)

    print(f"Latency result is saved to {filename}.")
    os.system(f"cat {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse latency results from benchmark logs')
    parser.add_argument('--system', '-s', required=True, choices=['oxbow', 'ext4'],
                        help='System name (oxbow or ext4)')
    args = parser.parse_args()

    find_and_parse_logs(args.system)
    write_latency_csv(args.system)
