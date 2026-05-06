import os
import re
import csv
from pathlib import Path
from collections import defaultdict


# path = "/home/koo/workspace/uFS/cfs_bench/exprs/DATA_microbench_omnicache_05-02-13-45-53"
# BASE_DIR = Path(path)

# 결과가 들어 있는 최상위 디렉토리
BASE_DIR = Path("/home/koo/workspace/uFS/cfs_bench/exprs/DATA_microbench_omnicache_latest")


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

# { experiment_name : [fsync_avg_ms, fsync_avg_ms, ...] }
# 한 bench_log_* 파일에서 뽑아낸 "Average fsync latency (ms)" 값을 누적
fsync_results = defaultdict(list)


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


def parse_fsync_time_from_log(filepath: Path, experiment: str):
    """
    bench_log_* 파일에서 fsync latency 통계를 파싱.
    예시 코드와 동일하게,
      - "Microseconds per fsync" 라인을 만나면 블록 시작
      - 그 다음 라인들 중 "Average:" 가 있는 라인의 평균(us)를 읽어서 ms로 변환
    한 파일당 평균 fsync(ms)를 하나의 값으로 보고 fsync_results[experiment] 리스트에 추가.
    """
    in_fsync_block = False

    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            # fsync 블록 시작
            if "Microseconds per fsync" in line:
                in_fsync_block = True
                continue

            # fsync 블록 안에서 Average 라인을 찾는다.
            if in_fsync_block and "Average:" in line:
                m = re.search(r"Average:\s+([\d.]+)", line)
                if m:
                    avg_us = float(m.group(1))
                    avg_ms = avg_us / 1000.0  # microseconds -> milliseconds
                    fsync_results[experiment].append(avg_ms)
                # 한 블록 처리 후 종료
                in_fsync_block = False


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
                # fsync latency도 같이 파싱 (write workload에서만 값이 있을 가능성이 큼)
                parse_fsync_time_from_log(log_file, exp)


def write_throughput_csv(filename: str = "throughput_results.csv"):
    """
    실험별 total throughput + fsync latency 통계를 CSV로 저장.
    컬럼:
      experiment, num_logs, total_throughput_MBps,
      avg_fsync_ms, min_fsync_ms, max_fsync_ms
    """
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "experiment",
            "num_logs",
            "total_throughput_MBps",
            "avg_fsync_ms",
            "min_fsync_ms",
            "max_fsync_ms",
        ])

        for exp in sorted(throughput_results.keys()):
            fsync_vals = fsync_results.get(exp, [])

            if fsync_vals:
                avg_ms = round(sum(fsync_vals) / len(fsync_vals), 4)
                min_ms = round(min(fsync_vals), 4)
                max_ms = round(max(fsync_vals), 4)
            else:
                # RDPS / RDPR 같이 fsync가 없거나, 로그에 없으면 빈 값
                avg_ms = ""
                min_ms = ""
                max_ms = ""

            writer.writerow([
                exp,
                file_counts[exp],
                throughput_results[exp],
                avg_ms,
                min_ms,
                max_ms,
            ])

    print(f"[INFO] 결과를 {filename} 파일로 저장했습니다.")


if __name__ == "__main__":
    find_and_parse_all_logs()
    write_throughput_csv()