#!/usr/bin/env python3
"""
Export .perf.script / sanity artifacts from perf.data and produce CPU usage CSV
matching microbench_performance_parse.py (perf report --sort comm, same columns).
"""
import argparse
import csv
import os
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_PERF_ROOT = Path(".")
PERF_NAME_PATTERNS = [
    re.compile(r"^perfthp_(\w+)_iosize(\d+)_(\d+)$"),
    re.compile(r"^Throughput-(\w+)-iosize(\d+)-(\d+)$"),
]
WORKLOAD_PRIORITY = {
    "append": 0,
    "seqwrite": 1,
    "rwrite": 2,
    "seqread": 3,
    "rread": 4,
}

CSV_FIELDS = [
    "workload",
    "iosize",
    "process",
    "app",
    "duration_sec",
    "cycles_per_sec",
    "percent_of_total_cycles",
]

PERF_SCRIPT_FIELDS = "comm,pid,tid,cpu,time,event,ip,sym,dso,trace"
SANITY_REPORT_PERCENT_LIMIT = "0.1"

# Same filtering as microbench_performance_parse.process_perf_file
COMM_REPORT_PERCENT_LIMIT = "0.1"
COMM_USAGE_LINE_PATTERN = re.compile(r"^\s*([\d.]+)%\s+(.+)$")
PERCENT_TOKEN_PATTERN = re.compile(r"^\d+(?:\.\d+)?%$")
PROCESS_PERCENT_THRESHOLD = 1.0
LEGACY_SCRIPT_TIME_PATTERN = re.compile(r"^\s*\S+\s+\d+\s+\[\d+\]\s+([\d.]+):")
EVENT_HEADER_PATTERN = re.compile(r"# Samples:.*of event '([^']+)'")
EVENT_COUNT_PATTERN = re.compile(r"Event count \(approx\.\):\s*([\d]+)")


def get_cpu_freq_hz():
    with open("/proc/cpuinfo", encoding="utf-8") as cpuinfo_file:
        for info_line in cpuinfo_file:
            if "cpu MHz" in info_line:
                mhz = float(info_line.strip().split(":")[1])
                return mhz * 1e6
    return 2.6e9


def parse_perf_name(perf_name):
    for perf_name_pattern in PERF_NAME_PATTERNS:
        match = perf_name_pattern.match(perf_name)
        if match:
            return match.groups()
    return None


def add_perf_file(perf_files, perf_file):
    parsed_name = parse_perf_name(perf_file.name)
    if not parsed_name:
        return

    workload, iosize_str, app_str = parsed_name
    iosize_val = int(iosize_str)
    app_val = int(app_str)
    workload_prio = WORKLOAD_PRIORITY.get(workload, 99)
    perf_files.append(
        (
            workload_prio,
            iosize_val,
            app_val,
            perf_file,
            workload,
            iosize_val,
            app_val,
        )
    )


def collect_perf_files(system_name, perf_root):
    perf_files = []
    if not perf_root.exists():
        return perf_files

    for perf_file in perf_root.iterdir():
        if perf_file.is_file():
            add_perf_file(perf_files, perf_file)

    run_pattern = f"{system_name}_*_run_0"
    for run_dir in perf_root.rglob(run_pattern):
        app_pattern = f"log_{system_name}_*_throughput_app_*"
        for app_dir in run_dir.rglob(app_pattern):
            for perf_file in app_dir.rglob("perfthp_*"):
                if not perf_file.is_file():
                    continue
                if perf_file.parent.name != "perf":
                    continue

                add_perf_file(perf_files, perf_file)

    perf_files.sort()
    return perf_files


def perf_script_extra_args(kallsyms_path):
    if kallsyms_path:
        return ["--kallsyms", str(kallsyms_path)]
    return []


def export_breakdown_perf_script(perf_path_arg, kallsyms_path):
    """
    Matches manual workflow:
      perf script -i perf.data --fields ... > perf.script
    Writes sibling file: <perf.data path>.perf.script
    """
    out_path = Path(f"{perf_path_arg}.perf.script")
    script_args = [
        "perf",
        "script",
        "-i",
        str(perf_path_arg),
        "--fields",
        PERF_SCRIPT_FIELDS,
    ]
    script_args.extend(perf_script_extra_args(kallsyms_path))

    proc = subprocess.run(
        script_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        perf_input = Path(perf_path_arg)
        print(
            "WARNING: perf script export failed "
            f"for {perf_input.resolve()} rc={proc.returncode}: {proc.stderr.strip()}"
        )
        return None

    try:
        with open(out_path, "w", encoding="utf-8", newline="\n") as script_file:
            script_file.write(proc.stdout)
    except OSError as export_err:
        print(f"WARNING: could not write {out_path.resolve()}: {export_err}")
        return None

    # print(f"Wrote {out_path.resolve()}")
    return out_path


def write_breakdown_sanity_report(perf_path_arg, kallsyms_path):
    """
    Sanity check (human-readable), same sorting as manual:
      perf report -i ... --stdio --sort comm,dso,symbol --percent-limit 0.1
    """
    out_path = Path(f"{perf_path_arg}.report_sanity.txt")
    report_args = [
        "perf",
        "report",
        "-i",
        str(perf_path_arg),
        "--stdio",
        "--sort",
        "comm,dso,symbol",
        "--percent-limit",
        SANITY_REPORT_PERCENT_LIMIT,
    ]
    report_args.extend(perf_script_extra_args(kallsyms_path))

    proc = subprocess.run(
        report_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        perf_input = Path(perf_path_arg)
        print(
            "WARNING: perf report sanity failed "
            f"for {perf_input.resolve()} rc={proc.returncode}: {proc.stderr.strip()}"
        )
        return None

    try:
        with open(out_path, "w", encoding="utf-8", newline="\n") as sanity_file:
            sanity_file.write(proc.stdout)
    except OSError as write_err:
        print(f"WARNING: could not write {out_path.resolve()}: {write_err}")
        return None

    # print(f"Wrote sanity perf report {out_path.resolve()}")
    return out_path


def extract_process_name_from_comm_report_line(report_line):
    matched = COMM_USAGE_LINE_PATTERN.match(report_line)
    if not matched:
        return None

    percent_value = float(matched.group(1))
    if percent_value < PROCESS_PERCENT_THRESHOLD:
        return None

    remaining_columns = matched.group(2).split()
    while remaining_columns and PERCENT_TOKEN_PATTERN.match(remaining_columns[0]):
        remaining_columns.pop(0)
    if not remaining_columns:
        return None

    return remaining_columns[0], percent_value


def extract_duration_legacy_parse_style(perf_path_arg):
    """
    Same timing as microbench_performance_parse.process_perf_file (plain perf script).
    Does not pass --kallsyms, matching legacy script behaviour.
    """
    script_run = subprocess.run(
        ["perf", "script", "-i", str(perf_path_arg)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    times = []
    for script_line in script_run.stdout.splitlines():
        match = LEGACY_SCRIPT_TIME_PATTERN.search(script_line)
        if match:
            times.append(float(match.group(1)))

    if not times:
        return None

    duration_local = max(times) - min(times)
    if duration_local <= 0:
        return None
    return duration_local


def parse_comm_report_weighted_cycles(report_stdout):
    """
    Parse perf report --sort comm output and combine multiple events correctly.

    perf reports each event section relative to that event's own total. For a
    record with cycles:u and cycles:k, raw percentages therefore sum to about
    200%. Convert each event-local percentage back to cycles, then normalize by
    the sum of event counts.
    """
    current_event = "default"
    event_counts = {}
    process_percent_by_event = defaultdict(lambda: defaultdict(float))

    for report_line in report_stdout.splitlines():
        event_header = EVENT_HEADER_PATTERN.search(report_line)
        if event_header:
            current_event = event_header.group(1)
            continue

        event_count = EVENT_COUNT_PATTERN.search(report_line)
        if event_count:
            event_counts[current_event] = event_counts.get(current_event, 0) + int(
                event_count.group(1)
            )
            continue

        process_percent = extract_process_name_from_comm_report_line(report_line)
        if process_percent is None:
            continue

        process_name, percent_value = process_percent
        process_percent_by_event[current_event][process_name] += percent_value

    if not event_counts:
        return None, {}

    process_cycles = defaultdict(float)
    for event_name, event_total_cycles in event_counts.items():
        for process_name, percent_value in process_percent_by_event[event_name].items():
            process_cycles[process_name] += event_total_cycles * (percent_value / 100.0)

    return sum(event_counts.values()), process_cycles


def process_perf_file(
    perf_path_arg,
    workload_name,
    iosize_bytes,
    app_count,
    kallsyms_path,
):
    try:
        write_breakdown_sanity_report(perf_path_arg, kallsyms_path)

        export_breakdown_perf_script(perf_path_arg, kallsyms_path)

        report_args = [
            "perf",
            "report",
            "-i",
            str(perf_path_arg),
            "--stdio",
            "--sort",
            "comm",
            "--percent-limit",
            COMM_REPORT_PERCENT_LIMIT,
        ]
        # Match microbench_performance_parse.py: no --kallsyms on this report command.
        report_run = subprocess.run(
            report_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        report_output_text = report_run.stdout

        total_cycles, process_cycles_dict = parse_comm_report_weighted_cycles(
            report_output_text
        )
        if total_cycles is None:
            return []

        if not process_cycles_dict:
            return []

        duration_sec = extract_duration_legacy_parse_style(perf_path_arg)
        if duration_sec is None:
            return []

        thread_results = []
        for process_entry, process_cycles in process_cycles_dict.items():
            pct = process_cycles / total_cycles * 100.0
            cps_local = process_cycles / duration_sec
            thread_results.append(
                {
                    "workload": workload_name,
                    "iosize": iosize_bytes,
                    "process": process_entry,
                    "app": app_count,
                    "duration_sec": round(duration_sec, 2),
                    "cycles_per_sec": round(cps_local, 2),
                    "percent_of_total_cycles": round(pct, 2),
                }
            )

        return thread_results
    except (ValueError, OSError):
        return []


def process_perf_files(perf_files, kallsyms_path, workers):
    results = []
    max_workers_run = min(workers, os.cpu_count() or workers)
    futures = []

    with ThreadPoolExecutor(max_workers=max_workers_run) as executor_proc:
        for _, _, _, perf_path_run, workload, iosize_run, app in perf_files:
            futures.append(
                executor_proc.submit(
                    process_perf_file,
                    perf_path_run,
                    workload,
                    iosize_run,
                    app,
                    kallsyms_path,
                )
            )

        for future in as_completed(futures):
            file_results_ready = future.result()
            if file_results_ready:
                results.extend(file_results_ready)

    results.sort(
        key=lambda row: (
            WORKLOAD_PRIORITY.get(row["workload"], 99),
            row["iosize"],
            row["app"],
            row["process"],
        )
    )

    return results


def save_results(system_name_arg, results, output_dir_arg):
    output_dir_arg.mkdir(parents=True, exist_ok=True)
    csv_name = output_dir_arg / f"{system_name_arg}_cpu_usage_results.csv"
    with open(csv_name, "w", newline="", encoding="utf-8") as csv_opened:
        writer = csv.DictWriter(csv_opened, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row_saved in results:
            writer.writerow(row_saved)

    print(f"Results saved to {csv_name.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Microbench perf.data: writes <perf>.perf.script (--fields export), "
            ".report_sanity.txt, "
            "and CPU CSV matching microbench_performance_parse.py "
            "(perf report --sort comm --percent-limit 0.1, process rows >= 1%%)."
        )
    )
    parser.add_argument(
        "--system",
        "-s",
        default="uFS",
        choices=["uFS", "oxbow", "ext4"],
        help="System name (default: uFS)",
    )
    parser.add_argument(
        "--perf-root",
        type=Path,
        default=DEFAULT_PERF_ROOT,
        help=(
            "Directory containing perf.data files "
            "(default: current directory)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=".",
        type=Path,
        help="Directory for <system>_cpu_usage_results.csv",
    )
    parser.add_argument(
        "--kallsyms",
        default="/proc/kallsyms",
        type=Path,
        help="kallsyms path for exported perf script / sanity report only",
    )
    parser.add_argument(
        "--workers",
        default=8,
        type=int,
        help="Maximum worker threads",
    )
    cli_args = parser.parse_args()

    cpu_hz = get_cpu_freq_hz()
    core_ct = os.cpu_count() or 8
    print(f"Detected CPU frequency: {cpu_hz / 1e9:.2f} GHz")
    print(f"Detected logical cores: {core_ct}")

    ksym = cli_args.kallsyms if cli_args.kallsyms.exists() else None
    if ksym is None:
        print(
            "Warning: kallsyms path not found; exported script / sanity "
            "may show unknown kernel symbols."
        )

    perf_root = cli_args.perf_root.resolve()
    print(f"Perf root: {perf_root}")
    perf_list = collect_perf_files(cli_args.system, perf_root)
    print(f"Found {len(perf_list)} perf files for {cli_args.system}")

    aggregated = process_perf_files(perf_list, ksym, cli_args.workers)
    save_results(cli_args.system, aggregated, cli_args.output_dir)


if __name__ == "__main__":
    main()

