import csv
import os
import re
from collections import defaultdict
from pathlib import Path

# Execute relative to the working directory
BASE_DIR = Path(".")

# Map directory name to operation name
dir_to_op = {
    "ADPS": "append",
    "WDPS": "sequential write",
    "WDPR": "random write",
    "RDPS": "sequential read",
    "RDPR": "random read",
    # Add more if needed
}

op_order = ["ADPS", "WDPS", "WDPR", "RDPS", "RDPR"]

# {(operation, io_size_KB, process_count) : total_throughput_MBps}
throughput_results = defaultdict(float)


def parse_throughput_from_log(filepath, operation, process_count):
    with open(filepath, "r") as f:
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
    for subdir in BASE_DIR.rglob("oxbow_*_run_0"):
        match_dir = re.search(r"oxbow_(ADPS|WDPS|WDPR|RDPS|RDPR)_run_0", str(subdir))
        if not match_dir:
            print(f"Skipping {subdir} as it does not match expected pattern.")
            continue

        op_key = match_dir.group(1)
        subdirs.append((op_key, subdir))

    # Sort in the desired order
    subdirs.sort(key=lambda x: op_order.index(x[0]))

    for op_key, subdir in subdirs:
        operation = dir_to_op.get(op_key)
        if not operation:
            continue

        app_dirs = []
        for app_dir in subdir.glob("log_oxbow_*_throughput*"):
            match_app = re.search(r"(\d+)$", app_dir.name)  # Trailing number in directory name
            if not match_app:
                continue
            process_count = int(match_app.group(1))
            app_dirs.append((process_count, app_dir))

        # Sort ascending by the numeric value
        app_dirs.sort(key=lambda x: x[0])

        # Parse log files
        for process_count, app_dir in app_dirs:
            for log_file in app_dir.rglob("bench_log_*"):
                if log_file.is_file():
                    parse_throughput_from_log(log_file, operation, process_count)


def write_throughput_csv(filename="throughput_results.csv"):
    op_order = [
        "append",
        "sequential write",
        "random write",
        "sequential read",
        "random read",
    ]

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["operation", "io size (K)", "process", "total throughput (MB/s)"]
        )

        # Sort by: operation → io_size → process_count
        sorted_keys = sorted(
            throughput_results.keys(),
            key=lambda x: (op_order.index(x[0]), x[1], x[2]),  # io_size is an integer
        )

        for operation, io_size, process_count in sorted_keys:
            writer.writerow(
                [
                    operation,
                    f"{io_size}K",
                    process_count,
                    throughput_results[(operation, io_size, process_count)],
                ]
            )


if __name__ == "__main__":
    find_and_parse_all_logs()
    write_throughput_csv()
