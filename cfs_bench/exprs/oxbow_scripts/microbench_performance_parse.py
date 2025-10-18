import csv
import os
import re
from pathlib import Path

# Configuration
base_dir = Path(".")
perf_pattern = re.compile(r"Throughput-(\w+)-iosize(\d+)-(\d+)$")

# Workload priority
workload_priority = {"append": 0, "seqwrite": 1, "rwrite": 2, "seqread": 3, "rread": 4}

# Detect system information automatically
def get_cpu_freq_hz():
    with open("/proc/cpuinfo") as f:
        for line in f:
            if "cpu MHz" in line:
                mhz = float(line.strip().split(":")[1])
                return mhz * 1e6  # MHz → Hz
    return 2.6e9  # fallback

cpu_freq = get_cpu_freq_hz()
core_count = os.cpu_count() or 8  # Logical cores, default 8

# Collect and sort perf files
perf_files = []
for perf_file in base_dir.glob("Throughput-*-iosize*-*"):
    match = perf_pattern.match(perf_file.name)
    if match:
        workload, iosize, app = match.groups()
        iosize_val = int(iosize)
        app_val = int(app)
        workload_prio = workload_priority.get(workload, 99)
        perf_files.append((workload_prio, iosize_val, app_val, perf_file))

# Sort
perf_files.sort()

# Container for aggregated results
results = []

# Iterate over all perf files
for _, _, _, perf_file in perf_files:
    match = perf_pattern.match(perf_file.name)
    if not match:
        continue
    workload, iosize, app = match.groups()
    iosize = iosize
    app = int(app)

    # Run perf report
    report_cmd = f"perf report -i {perf_file} --stdio --sort comm --percent-limit 0.1"
    report_output = os.popen(report_cmd).read()

    # Extract total cycle count
    event_match = re.search(r"Event count \(approx.\):\s*([\d]+)", report_output)
    if not event_match:
        continue
    total_cycles = int(event_match.group(1))

    # Extract per-process percentage (only >= 1%)
    process_usage = {}
    pattern = re.compile(r"^\s*([\d.]+)%\s+(\S+)")
    for line in report_output.splitlines():
        match = pattern.match(line)
        if match:
            percent = float(match.group(1))
            if percent >= 1.0:
                process = match.group(2)
                process_usage[process] = process_usage.get(process, 0) + percent

    # Run perf script and extract timestamps
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

    # Compute cycles per process
    for process, percent in process_usage.items():
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

# Save to CSV
with open("cpu_usage_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "workload", "iosize", "process", "app",
        "duration_sec", "cycles_per_sec", "percent_of_total_cycles"
    ])
    writer.writeheader()
    for row in results:
        writer.writerow(row)

print("Results saved to cpu_usage_results.csv")
