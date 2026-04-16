#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

RUN_DIR_RE = re.compile(r"^(?P<fs>fsp|ext4)_(?P<run_code>[A-Za-z0-9]+)_run_(?P<run_id>\d+)$")
BENCH_LOG_RE = re.compile(r"^bench_log_(?P<app_index>\d+)$")

RUN_CODE_TO_WORKLOAD = {
    "S1MP": "stat",
    "S1MS": "stat",
    "SaMP": "statall",
    "SaMS": "statall",
    "LsMP": "listdir",
    "LsMS": "listdir",
    "CMP": "create",
    "CMS": "create",
    "UMP": "unlink",
    "UMS": "unlink",
    "RMP": "rename",
    "RMS": "rename",
}

RUN_CODE_TO_EXPECTED_BENCHMARKS = {
    "S1MP": {"stat1"},
    "S1MS": {"stat1"},
    "SaMP": {"listdirinfo2"},
    "SaMS": {"listdirinfo2"},
    "LsMP": {"listdir", "listdirinfo1"},
    "LsMS": {"listdir", "listdirinfo1"},
    "CMP": {"create"},
    "CMS": {"create"},
    "UMP": {"unlink"},
    "UMS": {"unlink"},
    "RMP": {"rename"},
    "RMS": {"rename"},
}

RUN_CODE_ORDER = [
    "S1MP",
    "S1MS",
    "SaMP",
    "SaMS",
    "LsMP",
    "LsMS",
    "CMP",
    "CMS",
    "UMP",
    "UMS",
    "RMP",
    "RMS",
]
RUN_CODE_ORDER_INDEX = {name: idx for idx, name in enumerate(RUN_CODE_ORDER)}
FILESYSTEM_ORDER_INDEX = {"ufs": 0, "ext4": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse metadata microbenchmark logs from a single filesystem result "
            "directory, then generate raw and summary CSV files."
        )
    )
    parser.add_argument(
        "result_path",
        type=Path,
        help=(
            "Path to a directory that contains data_result, or the data_result "
            "directory itself."
        ),
    )
    parser.add_argument(
        "system",
        choices=["ufs", "ext4"],
        help="Filesystem type of the input result path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory where output CSV files are written. "
            "Default: resolved result directory."
        ),
    )
    parser.add_argument(
        "--raw-csv-name",
        type=str,
        default="metadata_results_raw.csv",
        help="Output CSV name for per-log parsed rows.",
    )
    parser.add_argument(
        "--summary-csv-name",
        type=str,
        default="metadata_results_summary.csv",
        help="Output CSV name for aggregated rows.",
    )
    return parser.parse_args()


def looks_like_result_dir(path: Path, filesystem: str) -> bool:
    run_prefix = get_run_prefix(filesystem)
    try:
        for child in path.iterdir():
            if not child.is_dir():
                continue
            run_match = RUN_DIR_RE.match(child.name)
            if run_match is None:
                continue
            if run_match.group("fs") == run_prefix:
                return True
    except OSError:
        return False
    return False


def resolve_data_result_dir(result_path: Path, filesystem: str) -> Path:
    resolved = result_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Result path does not exist: {resolved}")
    if not resolved.is_dir():
        raise NotADirectoryError(f"Result path is not a directory: {resolved}")

    if looks_like_result_dir(resolved, filesystem):
        return resolved

    data_result_dir = resolved / "data_result"
    if data_result_dir.is_dir() and looks_like_result_dir(data_result_dir, filesystem):
        return data_result_dir.resolve()

    raise FileNotFoundError(
        "No parseable result directory found. "
        f"Tried: {resolved} and {data_result_dir} (system={filesystem})."
    )


def get_run_prefix(filesystem: str) -> str:
    if filesystem == "ufs":
        return "fsp"
    if filesystem == "ext4":
        return "ext4"
    raise ValueError(f"Unsupported filesystem: {filesystem}")


def parse_json_result_line(log_path: Path) -> Optional[Dict[str, Any]]:
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if '"json_magic"' not in line:
                    continue
                start = line.find("{")
                end = line.rfind("}")
                if start == -1 or end == -1 or end <= start:
                    continue
                payload = line[start : end + 1]
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return None
    return None


def should_keep_log(run_code: str, benchmark: str) -> bool:
    expected_benchmarks = RUN_CODE_TO_EXPECTED_BENCHMARKS.get(run_code)
    if expected_benchmarks is None:
        return False
    return benchmark in expected_benchmarks


def to_float(value: Any, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def collect_records(root_dir: Path, filesystem: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    run_prefix = get_run_prefix(filesystem)
    app_dir_re = re.compile(rf"^log_{run_prefix}_.+_app_(?P<app_count>\d+)$")
    stats = {
        "run_dirs_seen": 0,
        "app_dirs_seen": 0,
        "bench_logs_seen": 0,
        "bench_logs_parsed": 0,
        "bench_logs_kept": 0,
        "bench_logs_dropped": 0,
    }
    records: List[Dict[str, Any]] = []

    for run_dir in sorted((p for p in root_dir.iterdir() if p.is_dir()), key=lambda p: p.name):
        run_match = RUN_DIR_RE.match(run_dir.name)
        if run_match is None:
            continue
        if run_match.group("fs") != run_prefix:
            continue
        stats["run_dirs_seen"] += 1

        run_code = run_match.group("run_code")
        run_id = to_int(run_match.group("run_id"), default=0)
        workload = RUN_CODE_TO_WORKLOAD.get(run_code, run_code.lower())
        sharing_mode = "shared" if run_code.endswith("S") else "private"

        for app_dir in sorted((p for p in run_dir.iterdir() if p.is_dir()), key=lambda p: p.name):
            app_match = app_dir_re.match(app_dir.name)
            if app_match is None:
                continue
            stats["app_dirs_seen"] += 1
            app_count = to_int(app_match.group("app_count"), default=0)

            for bench_log in sorted((p for p in app_dir.rglob("bench_log_*") if p.is_file()), key=lambda p: p.as_posix()):
                stats["bench_logs_seen"] += 1
                idx_match = BENCH_LOG_RE.match(bench_log.name)
                if idx_match is None:
                    continue
                app_index = to_int(idx_match.group("app_index"), default=-1)

                parsed = parse_json_result_line(bench_log)
                if parsed is None:
                    continue
                stats["bench_logs_parsed"] += 1

                benchmark = str(parsed.get("benchmark", ""))
                if not should_keep_log(run_code, benchmark):
                    stats["bench_logs_dropped"] += 1
                    continue

                num_ops = to_int(parsed.get("num_ops"), default=0)
                microseconds = to_float(parsed.get("microseconds"))
                throughput_ops_per_sec = to_float(parsed.get("throughput"))
                latency_us = to_float(parsed.get("latency"))

                if (not math.isfinite(throughput_ops_per_sec) or throughput_ops_per_sec <= 0) and num_ops > 0 and math.isfinite(microseconds) and microseconds > 0:
                    throughput_ops_per_sec = num_ops / (microseconds / 1_000_000.0)
                if (not math.isfinite(latency_us) or latency_us <= 0) and num_ops > 0 and math.isfinite(microseconds) and microseconds > 0:
                    latency_us = microseconds / num_ops

                record = {
                    "filesystem": filesystem,
                    "run_code": run_code,
                    "run_id": run_id,
                    "workload": workload,
                    "sharing_mode": sharing_mode,
                    "app_count": app_count,
                    "app_index": app_index,
                    "benchmark": benchmark,
                    "num_ops": num_ops,
                    "microseconds": microseconds,
                    "throughput_ops_per_sec": throughput_ops_per_sec,
                    "latency_us": latency_us,
                    "timestamp_dir": bench_log.parent.parent.name,
                    "phase_dir": bench_log.parent.name,
                    "bench_log_path": str(bench_log),
                }
                records.append(record)
                stats["bench_logs_kept"] += 1

    return records, stats


def summarize_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in records:
        key = (
            row["filesystem"],
            row["run_code"],
            row["run_id"],
            row["workload"],
            row["sharing_mode"],
            row["app_count"],
        )
        grouped[key].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for key, items in grouped.items():
        filesystem, run_code, run_id, workload, sharing_mode, app_count = key

        total_ops = sum(to_int(item["num_ops"]) for item in items)
        total_throughput = sum(to_float(item["throughput_ops_per_sec"], default=0.0) for item in items)

        total_microseconds = 0.0
        valid_microseconds_count = 0
        lat_weighted_sum = 0.0
        lat_weighted_ops = 0
        lat_sum = 0.0
        lat_valid_count = 0

        for item in items:
            microseconds = to_float(item["microseconds"])
            if math.isfinite(microseconds):
                total_microseconds += microseconds
                valid_microseconds_count += 1

            latency = to_float(item["latency_us"])
            ops = to_int(item["num_ops"])
            if math.isfinite(latency):
                lat_sum += latency
                lat_valid_count += 1
                if ops > 0:
                    lat_weighted_sum += latency * ops
                    lat_weighted_ops += ops

        weighted_latency = lat_weighted_sum / lat_weighted_ops if lat_weighted_ops > 0 else math.nan
        avg_latency = lat_sum / lat_valid_count if lat_valid_count > 0 else math.nan
        avg_runtime_sec = (total_microseconds / valid_microseconds_count) / 1_000_000.0 if valid_microseconds_count > 0 else math.nan
        summed_runtime_sec = total_microseconds / 1_000_000.0 if valid_microseconds_count > 0 else math.nan

        summary_rows.append(
            {
                "filesystem": filesystem,
                "run_code": run_code,
                "run_id": run_id,
                "workload": workload,
                "sharing_mode": sharing_mode,
                "app_count": app_count,
                "num_logs": len(items),
                "total_ops": total_ops,
                "throughput_ops_per_sec_sum": total_throughput,
                "latency_us_weighted_avg": weighted_latency,
                "latency_us_simple_avg": avg_latency,
                "runtime_sec_sum": summed_runtime_sec,
                "runtime_sec_avg": avg_runtime_sec,
            }
        )

    summary_rows.sort(
        key=lambda row: (
            RUN_CODE_ORDER_INDEX.get(row["run_code"], 10_000),
            FILESYSTEM_ORDER_INDEX.get(row["filesystem"], 10_000),
            to_int(row["app_count"], default=10_000),
        )
    )
    return summary_rows


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    args = parse_args()
    system = args.system
    result_dir = resolve_data_result_dir(args.result_path, system)
    output_dir = result_dir if args.output_dir is None else args.output_dir.resolve()

    raw_rows, parse_stats = collect_records(result_dir, filesystem=system)
    raw_rows.sort(
        key=lambda row: (
            RUN_CODE_ORDER_INDEX.get(row["run_code"], 10_000),
            FILESYSTEM_ORDER_INDEX.get(row["filesystem"], 10_000),
            to_int(row["app_count"], default=10_000),
            to_int(row["app_index"], default=10_000),
        )
    )

    summary_rows = summarize_records(raw_rows)

    raw_csv_path = output_dir / args.raw_csv_name
    summary_csv_path = output_dir / args.summary_csv_name

    raw_fields = [
        "filesystem",
        "run_code",
        "run_id",
        "workload",
        "sharing_mode",
        "app_count",
        "app_index",
        "benchmark",
        "num_ops",
        "microseconds",
        "throughput_ops_per_sec",
        "latency_us",
        "timestamp_dir",
        "phase_dir",
        "bench_log_path",
    ]
    summary_fields = [
        "filesystem",
        "run_code",
        "run_id",
        "workload",
        "sharing_mode",
        "app_count",
        "num_logs",
        "total_ops",
        "throughput_ops_per_sec_sum",
        "latency_us_weighted_avg",
        "latency_us_simple_avg",
        "runtime_sec_sum",
        "runtime_sec_avg",
    ]

    write_csv(raw_csv_path, raw_rows, raw_fields)
    write_csv(summary_csv_path, summary_rows, summary_fields)

    print(f"Wrote raw CSV: {raw_csv_path}")
    print(f"Wrote summary CSV: {summary_csv_path}")
    print(f"Input system: {system}")
    print(f"Input result directory: {result_dir}")
    print(f"Parse stats: {parse_stats}")
    print(f"Total parsed rows: {len(raw_rows)}")
    print(f"Total summary rows: {len(summary_rows)}")


if __name__ == "__main__":
    main()
