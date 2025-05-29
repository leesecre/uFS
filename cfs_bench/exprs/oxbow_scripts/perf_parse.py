import os
import re
import csv
from pathlib import Path

# 설정
base_dir = Path(".")
perf_pattern = re.compile(r"perfthp_(\w+)_syncop(-?\d+)_iosize(\w+)_([\d]+)$")

# workload 우선순위
workload_priority = {"append": 0, "seqwrite": 1, "rwrite": 2}

# CPU 정보
def get_cpu_freq_hz():
    with open("/proc/cpuinfo") as f:
        for line in f:
            if "cpu MHz" in line:
                mhz = float(line.strip().split(":")[1])
                return mhz * 1e6
    return 2.6e9

cpu_freq = get_cpu_freq_hz()
core_count = os.cpu_count() or 8

# perf 파일 수집
perf_files = []
for perf_file in base_dir.glob("perfthp_*_syncop*_iosize*_*"):
    match = perf_pattern.match(perf_file.name)
    if match:
        workload, syncop, iosize, app = match.groups()
        syncop_val = int(syncop)
        workload_prio = workload_priority.get(workload, 99)
        iosize_val = 65536 if iosize.upper() == "64K" else int(iosize)
        app_val = int(app)
        perf_files.append((syncop_val, workload_prio, iosize_val, app_val, workload, iosize, app, perf_file))

# 정렬: syncop > workload > iosize > app 순
perf_files.sort()

results = []

# perf 처리
for syncop, _, _, _, workload, iosize, app, perf_file in perf_files:
    report_cmd = f"perf report -i {perf_file} --stdio --sort comm --percent-limit 0.1"
    report_output = os.popen(report_cmd).read()

    event_match = re.search(r"Event count \(approx.\):\s*([\d]+)", report_output)
    if not event_match:
        continue
    total_cycles = int(event_match.group(1))

    process_usage = {}
    pattern = re.compile(r"^\s*([\d.]+)%\s+(\S+)")
    for line in report_output.splitlines():
        match = pattern.match(line)
        if match:
            percent = float(match.group(1))
            if percent >= 1.0:
                process = match.group(2)
                process_usage[process] = process_usage.get(process, 0) + percent

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

    for process, percent in process_usage.items():
        process_cycles = total_cycles * (percent / 100)
        cps = process_cycles / duration
        results.append({
            "syncop": syncop,
            "workload": workload,
            "iosize": iosize,
            "app": app,
            "process": process,
            "duration_sec": round(duration, 2),
            "cycles_per_sec": round(cps, 2),
            "percent_of_total_cycles": round(percent, 2)
        })

# CSV 저장
with open("cpu_usage_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "syncop", "workload", "iosize", "app",
        "process", "duration_sec", "cycles_per_sec", "percent_of_total_cycles"
    ])
    writer.writeheader()
    for row in results:
        writer.writerow(row)

print("결과가 cpu_usage_results.csv 파일에 저장되었습니다.")
