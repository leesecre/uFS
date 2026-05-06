import os
import re
import csv
from pathlib import Path
from collections import defaultdict

# 결과가 들어 있는 최상위 디렉토리
#BASE_DIR = Path("/home/koo/workspace/uFS/cfs_bench/exprs/DATA_microbench_omnicache_latest")
BASE_DIR = Path("/home/koo/workspace/uFS/cfs_bench/exprs/DATA_microbench_omnicache_05-01-04-27-08")

# 여기 리스트에 "실험 목록"을 넣으면 됩니다.
# 예: ['ADPS', 'RDPS', 'RDPR'] 이런 식으로.
EXPERIMENTS = [
    "ADPS",
    "RDPS",
    "RDPR",
    "WDPS",
    "WDPR",
]

# { experiment_name : total_MBps }
throughput_results = defaultdict(float)

# { experiment_name : bench_log 파일 개수 }
file_counts = defaultdict(int)


def parse_throughput_from_log(filepath: Path, experiment: str):
    """한 bench_log_* 파일에서 'MB/s' 값을 모두 더해서 throughput_results[experiment]에 누적."""
    total_for_file = 0.0

    with filepath.open("r") as f:
        for line in f:
            if "MB/s" in line:
                m = re.search(r"([\d.]+)\s+MB/s", line)
                if m:
                    mbps = float(m.group(1))
                    total_for_file += mbps

    # 파일 전체에서 모은 throughput을 실험 단위로 누적
    throughput_results[experiment] += total_for_file
    file_counts[experiment] += 1


def find_and_parse_all_logs():
    """각 omnicache_{EXP}_run_0 디렉토리 아래의 bench_log_* 파일을 모두 찾아서 파싱."""
    for exp in EXPERIMENTS:
        run_dir = BASE_DIR / f"omnicache_{exp}_run_0"

        if not run_dir.exists():
            print(f"[WARN] {run_dir} 디렉토리가 존재하지 않습니다. (exp={exp})")
            continue

        # 의미 없는 서브디렉토리들을 모두 포함해서 bench_log_* 파일 검색
        log_files = list(run_dir.rglob("bench_log_*"))

        if not log_files:
            print(f"[WARN] {run_dir} 아래에서 bench_log_* 파일을 찾지 못했습니다. (exp={exp})")
            continue

        print(f"[INFO] {exp}: {len(log_files)}개의 bench_log_* 파일을 파싱합니다.")

        for log_file in log_files:
            if log_file.is_file():
                parse_throughput_from_log(log_file, exp)


def write_throughput_csv(filename: str = "throughput_results.csv"):
    """실험별 total throughput을 CSV로 저장."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["experiment", "num_logs", "total_throughput_MBps"])

        for exp in sorted(throughput_results.keys()):
            writer.writerow([
                exp,
                file_counts[exp],
                throughput_results[exp],
            ])

    print(f"[INFO] 결과를 {filename} 파일로 저장했습니다.")


if __name__ == "__main__":
    find_and_parse_all_logs()
    write_throughput_csv()