import os
import re
import csv
from pathlib import Path
from collections import defaultdict

# DATA_microbench_omnicache_* 를 모두 순회
ROOT_DIR = Path("/home/koo/workspace/uFS/cfs_bench/exprs")

# log directory 이름에서 workload / num_process 추출
LOG_DIR_PATTERN = re.compile(
    r"log_omnicache_([a-zA-Z]+)_.*_app_(\d+)"
)

WORKLOAD_KEYWORDS = ["append", "seqwrite", "seqread", "randwrite", "randread"]

def extract_workload_and_process(dirname: str):
    """log_omnicache_* 디렉토리 이름에서 workload type과 process count를 추출."""
    m = LOG_DIR_PATTERN.search(dirname)
    if m:
        workload = m.group(1)
        num_process = int(m.group(2))
        return workload, num_process
    return None, None


def parse_throughput_from_log(filepath: Path):
    """bench_log 파일에서 MB/s 값들을 모두 더함."""
    total = 0.0
    with filepath.open() as f:
        for line in f:
            if "MB/s" in line:
                m = re.search(r"([\d.]+)\s+MB/s", line)
                if m:
                    total += float(m.group(1))
    return total


def scan_all_data_dirs():
    """DATA_microbench_omnicache_* 디렉토리들을 모두 처리."""
    results = []

    for data_dir in ROOT_DIR.glob("DATA_microbench_omnicache_*"):
        if not data_dir.is_dir():
            continue

        print(f"[INFO] Processing DATA directory: {data_dir.name}")

        for run_dir in data_dir.glob("omnicache_*_run_0"):
            experiment = run_dir.name.split("_")[1]  # ADPS / RDPS / ...

            # log_omnicache_* 디렉토리 순회
            for log_dir in run_dir.rglob("log_omnicache_*"):
                if not log_dir.is_dir():
                    continue

                workload, num_process = extract_workload_and_process(log_dir.name)
                if workload is None:
                    continue

                # bench_log_* 파일 모두 찾기
                bench_logs = list(log_dir.rglob("bench_log_*"))
                if not bench_logs:
                    continue

                total_throughput = 0.0
                for log_file in bench_logs:
                    total_throughput += parse_throughput_from_log(log_file)

                results.append({
                    "data_dir": data_dir.name,
                    "experiment": experiment,
                    "workload": workload,
                    "num_process": num_process,
                    "num_logs": len(bench_logs),
                    "throughput": total_throughput,
                })

    return results


def write_csv(results, filename="throughput_results.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "data_dir",
            "experiment",
            "workload",
            "num_process",
            "num_logs",
            "total_throughput_MBps"
        ])

        for r in results:
            writer.writerow([
                r["data_dir"],
                r["experiment"],
                r["workload"],
                r["num_process"],
                r["num_logs"],
                r["throughput"]
            ])

    print(f"[INFO] CSV saved: {filename}")


if __name__ == "__main__":
    results = scan_all_data_dirs()
    write_csv(results)
