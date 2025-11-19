import argparse
import csv
import os
import re

## shlex was used previously; remove if not used elsewhere
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Configuration
base_dir = Path(".")
perf_name_pattern = re.compile(r"^perfthp_(\w+)_iosize(\d+)_(\d+)$")

# Workload priority
workload_priority = {"append": 0, "seqwrite": 1, "rwrite": 2, "seqread": 3, "rread": 4}

# Detect system information automatically
def get_cpu_freq_hz():
    with open("/proc/cpuinfo", encoding="utf-8") as f:
        for info_line in f:
            if "cpu MHz" in info_line:
                mhz = float(info_line.strip().split(":")[1])
                return mhz * 1e6  # MHz → Hz
    return 2.6e9  # fallback

cpu_freq = get_cpu_freq_hz()
core_count = os.cpu_count() or 8  # Logical cores, default 8

# Collect and sort perf files by scanning benchmark hierarchy
def collect_perf_files(system_name):
    perf_files = []
    pattern = f"{system_name}_*_run_0"
    for run_dir in base_dir.rglob(pattern):
        app_pattern = f"log_{system_name}_*_throughput_app_*"
        for app_dir in run_dir.rglob(app_pattern):
            for perf_file in app_dir.rglob("perfthp_*"):
                if not perf_file.is_file():
                    continue
                if perf_file.parent.name != "perf":
                    continue
                match = perf_name_pattern.match(perf_file.name)
                if not match:
                    continue
                workload, iosize_str, app_str = match.groups()
                iosize_val = int(iosize_str)
                app_val = int(app_str)
                workload_prio = workload_priority.get(workload, 99)
                perf_files.append((workload_prio, iosize_val, app_val, perf_file, workload, iosize_val, app_val))
    
    # Sort for deterministic processing
    perf_files.sort()
    return perf_files

def process_perf_file(perf_path_arg, workload_name, iosize_bytes, app_count):
    try:
        report_args = [
            "perf", "report", "-i", str(perf_path_arg),
            "--stdio", "--sort", "comm", "--percent-limit", "0.1"
        ]
        report_run = subprocess.run(report_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        report_output = report_run.stdout

        event_match = re.search(r"Event count \(approx\.\):\s*([\d]+)", report_output)
        if not event_match:
            return []
        total_cycles = int(event_match.group(1))

        process_usage = {}
        pattern = re.compile(r"^\s*([\d.]+)%\s+(\S+)")
        for report_line in report_output.splitlines():
            m = pattern.match(report_line)
            if m:
                percent = float(m.group(1))
                if percent >= 1.0:
                    process = m.group(2)
                    process_usage[process] = process_usage.get(process, 0) + percent

        script_args = ["perf", "script", "-i", str(perf_path_arg)]
        script_run = subprocess.run(script_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        script_output = script_run.stdout.splitlines()

        time_pattern = re.compile(r"^\s*\S+\s+\d+\s+\[\d+\]\s+([\d.]+):")
        times = []
        for script_line in script_output:
            m = time_pattern.search(script_line)
            if m:
                times.append(float(m.group(1)))
        if not times:
            return []

        start_time, end_time = min(times), max(times)
        duration = end_time - start_time
        if duration <= 0:
            return []

        thread_results = []
        for process, percent in process_usage.items():
            process_cycles = total_cycles * (percent / 100)
            cps = process_cycles / duration
            thread_results.append({
                "workload": workload_name,
                "iosize": iosize_bytes,
                "process": process,
                "app": app_count,
                "duration_sec": round(duration, 2),
                "cycles_per_sec": round(cps, 2),
                "percent_of_total_cycles": round(percent, 2)
            })
        return thread_results
    except (ValueError, OSError):
        return []

# Iterate over all perf files using a thread pool
def process_perf_files(perf_files):
    results = []
    max_workers = min(8, os.cpu_count() or 8)
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for _, _, _, perf_path, workload, iosize, app in perf_files:
            perf_path_obj = Path(perf_path)
            futures.append(executor.submit(process_perf_file, perf_path_obj, workload, iosize, app))

        for future in as_completed(futures):
            file_results_ready = future.result()
            if file_results_ready:
                results.extend(file_results_ready)
    
    # Sort results to ensure deterministic output order
    # Sort by: workload priority, iosize, app, process
    results.sort(key=lambda x: (
        workload_priority.get(x["workload"], 99),
        x["iosize"],
        x["app"],
        x["process"]
    ))
    return results

# Save to CSV
def save_results(system_name, results):
    filename = f"{system_name}_cpu_usage_results.csv"
    with open(filename, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=[
            "workload", "iosize", "process", "app",
            "duration_sec", "cycles_per_sec", "percent_of_total_cycles"
        ])
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Results saved to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse CPU usage results from perf logs')
    parser.add_argument('--system', '-s', required=True, choices=['oxbow', 'ext4'],
                        help='System name (oxbow or ext4)')
    args = parser.parse_args()

    perf_files = collect_perf_files(args.system)
    results = process_perf_files(perf_files)
    save_results(args.system, results)
