import os
import re
import csv
from pathlib import Path

# 설정
base_dir = Path(".")
perf_pattern = re.compile(r"Throughput-(\w+)(?:-iosize(\d+))?-(\d+)$")

# 우선순위 설정
workload_priority = {"seqwrite": 0, "seqread": 1, "rread": 2}

# 시스템 정보 자동 감지
def get_cpu_freq_hz():
    with open("/proc/cpuinfo") as f:
        for line in f:
            if "cpu MHz" in line:
                mhz = float(line.strip().split(":")[1])
                return mhz * 1e6  # MHz → Hz
    return 2.6e9  # fallback

cpu_freq = get_cpu_freq_hz()
core_count = os.cpu_count() or 8  # 논리 코어 수, 기본값 8

# 파일 리스트 정렬해서 수집
perf_files = []
for perf_file in base_dir.glob("Throughput-*"):
    match = perf_pattern.match(perf_file.name)
    if match:
        workload, iosize, app = match.groups()
        iosize_val = int(iosize) if iosize else float("inf")  # 'unknown'은 마지막으로
        app_val = int(app)
        workload_prio = workload_priority.get(workload, 99)
        perf_files.append((workload_prio, iosize_val, app_val, perf_file))

# 정렬
perf_files.sort()

# 결과 저장 리스트
results = []

# 전체 perf 파일 순회
for _, _, _, perf_file in perf_files:
    match = perf_pattern.match(perf_file.name)
    if not match:
        continue
    workload, iosize, app = match.groups()
    iosize = iosize or "unknown"
    app = int(app)

    # perf report 실행
    report_cmd = f"perf report -i {perf_file} --stdio --sort comm --percent-limit 0.1"
    report_output = os.popen(report_cmd).read()

    # 총 사이클 수 추출
    event_match = re.search(r"Event count \(approx.\):\s*([\d]+)", report_output)
    if not event_match:
        continue
    total_cycles = int(event_match.group(1))

    # 프로세스별 비율 추출 (상위 10개만)
    process_usage = {}
    pattern = re.compile(r"^\s*([\d.]+)%\s+(\S+)")
    for line in report_output.splitlines():
        match = pattern.match(line)
        if match:
            percent = float(match.group(1))
            process = match.group(2)
            process_usage[process] = process_usage.get(process, 0) + percent
    sorted_process_usage = sorted(process_usage.items(), key=lambda x: x[1], reverse=True)[:10]

    # perf script 실행해서 시간 추출
    script_cmd = f"perf script -i {perf_file}"
    script_output = os.popen(script_cmd).read().splitlines()

    time_pattern = re.compile(r"^\s*\S+\s+\d+\s+\[\d+\]\s+([\d.]+):")
    times = [float(m.group(1)) for line in script_output if (m := time_pattern.search(line))]
    if not times:
        continue

    start_time, end_time = min(times), max(times)
    duration = end_time - start_time
    if duration <= 0:
        continue

    # 프로세스별 사이클 계산
    for process, percent in sorted_process_usage:
        process_cycles = total_cycles * (percent / 100)
        cps = process_cycles / duration
        results.append({
            "workload": workload,
            "iosize": iosize,
            "process": process,
            "app": app,
            "duration_sec": round(duration, 2),
            "cycles_per_sec": round(cps, 2),
            "percent_of_total_cycles": round(percent, 2)
        })

# CSV로 저장
with open("cpu_usage_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "workload", "iosize", "process", "app",
        "duration_sec", "cycles_per_sec", "percent_of_total_cycles"
    ])
    writer.writeheader()
    for row in results:
        writer.writerow(row)

print("결과가 cpu_usage_results.csv 파일에 저장되었습니다.")