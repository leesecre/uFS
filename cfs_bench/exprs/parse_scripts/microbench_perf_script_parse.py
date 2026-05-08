#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

# Matches perf.data siblings written by microbench_performance_parse_breakdown export:
#   perf script -i perf.data --fields comm,pid,tid,cpu,time,event,ip,sym,dso,trace
DEFAULT_PERF_ROOT = Path(".")
SCRIPT_SUFFIX = ".perf.script"
PERF_SCRIPT_NAME_PATTERNS = [
    re.compile(r"^perfthp_(\w+)_iosize(\d+)_(\d+)$"),
    re.compile(r"^Throughput-(\w+)-iosize(\d+)-(\d+)$"),
]
WORKLOAD_RANK = {
    "append": 0,
    "seqwrite": 1,
    "rwrite": 2,
    "seqread": 3,
    "rread": 4,
}

CSV_FIELDS = [
    "workload",
    "iosize",
    "app",
    "component",
    "cpu_mode",
    "samples",
    "weighted_samples",
    "percent_of_kept_samples",
    "duration_sec",
    "samples_per_sec",
]

DETAIL_FIELDS = [
    "workload",
    "iosize",
    "app",
    "component",
    "cpu_mode",
    "comm",
    "top_symbol",
    "top_dso",
    "samples",
    "weighted_samples",
    "percent_of_kept_samples",
]

EXCLUDED_COMM = {
    "perf",
    "swapper",
    "node",
    "git",
    "rg",
    "cfs_bench_coord",
    "cpuUsage.sh",
    "ps",
    "ls",
    "tmux:",
    "zsh",
    "htop",
    "sshd-session",
    "systemd-journal",
    "systemd-network",
    "watch",
    "sh",
    "bash",
    "free",
    "sleep",
    "cat",
    "sed",
    "python3",
    "irqbalance",
    "rcu_preempt",
    "grep",
    "ssh",
}

DEFAULT_LIBFS_REGEX = (
    r"(liboxbow_libfs|libufs|libfs|libsyscall_intercept|syscall_intercept|"
    r"intercept_|intercept_routine|intercept_wrapper|intercept_log_syscall|"
    r"devfs|rpc|pf_track|lock_page|unlock_page|dirty_page|hook)"
)

DEFAULT_JOURNAL_REGEX = r"(jnl|jbd2|journal_worker|checkpoint|commit)"

SCRIPT_SAMPLE_RE = re.compile(
    r"^\s*(?P<comm>.+?)\s+"
    r"(?P<pid>\d+)(?:/(?P<tid>\d+))?\s+"
    r"\[(?P<cpu>\d+)\]\s+"
    r"(?P<time>\d+(?:\.\d+)?):\s+"
    r"(?:(?P<period>\d+)\s+)?"
    r"(?P<event>\S+):"
)

STACK_FRAME_RE = re.compile(
    r"^\s+(?P<ip>[0-9a-fA-F]+)\s+" r"(?P<symbol>.*?)" r"(?:\s+\((?P<dso>.*)\))?\s*$"
)

# One-line samples from: perf script --fields comm,pid,tid,cpu,time,event,...
# Optional sample count may appear between timestamp and event (perf versions).
FIELDS_SAMPLE_HEAD_RE = re.compile(
    r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+\.\d+):?\s+(?:(\d+)\s+)?(cycles:[uk])\s+(.+)$"
)


def normalize_system(system: str) -> str:
    if system == "ext4":
        return "ext4-journal"
    return system


def normalize_workload(workload: str) -> str:
    workload_map = {
        "append": "append",
        "seqwrite": "seq write",
        "rwrite": "random write",
        "seqread": "seq read",
        "rread": "random read",
    }
    return workload_map.get(workload, workload)


def parse_cpu_mode(event: str) -> str:
    event = event.strip()
    if event.endswith(":u") or event.endswith("/u") or event.endswith(":uH"):
        return "user"
    if event.endswith(":k") or event.endswith("/k") or event.endswith(":kH"):
        return "kernel"
    return "unknown"


def is_excluded_comm(comm: str) -> bool:
    return (
        comm in EXCLUDED_COMM
        or comm.startswith("kworker")
        or comm.startswith("ksoftirqd")
        or comm.startswith("tmux")
        or comm.startswith("sshd")
    )


def is_benchmark_comm(comm: str) -> bool:
    return comm in {"cfs_bench", "cfs_bench_posix"} or comm.startswith("cfs_bench")


def is_ufs_server_comm(comm: str) -> bool:
    return comm == "fsMain"


def is_oxbow_server_comm(comm: str) -> bool:
    return (
        comm in {"secure_daemon", "_oxbow_ioworker", "_rpc_devfs_hand", "fsMain"}
        or comm.startswith("_msg_async")
        or comm.startswith("illufs_")
        or comm.startswith("_oxb_d_worker")
    )


def is_journal_comm(comm: str) -> bool:
    return comm.startswith("jbd2") or comm == "jnl_worker"


def stack_text(frames) -> str:
    return "\n".join(
        f"{frame['symbol']} {frame.get('dso', '')}" for frame in frames
    ).lower()


def stack_matches(frames, pattern) -> bool:
    for frame in frames:
        frame_text = f"{frame['symbol']} {frame.get('dso', '')}"
        if pattern.search(frame_text):
            return True
    return False


def top_frame(frames):
    if not frames:
        return {"symbol": "[no stack]", "dso": "[no dso]"}
    return frames[0]


def classify_sample(system, comm, cpu_mode, frames, libfs_re, journal_re):
    if is_excluded_comm(comm):
        return None

    text = stack_text(frames)

    if system == "ext4-journal":
        if is_journal_comm(comm) or journal_re.search(text):
            return "journaling (jbd2)"
        if is_benchmark_comm(comm):
            if cpu_mode == "kernel":
                return "kernel (VFS + ext4)"
            return "benchmark application"
        return f"other {cpu_mode}"

    if system == "uFS":
        if comm.startswith("jbd2"):
            return None
        if is_ufs_server_comm(comm):
            return "file server process"
        if is_benchmark_comm(comm):
            if cpu_mode == "kernel":
                return "kernel"
            if stack_matches(frames, libfs_re):
                return "library file system"
            return "benchmark application"
        return f"other {cpu_mode}"

    if system == "oxbow":
        if comm.startswith("jbd2"):
            return None
        if comm == "jnl_worker" or journal_re.search(text):
            return "background journaling thread"
        if is_oxbow_server_comm(comm) or re.search(
            r"(dir_epoll_loop|lwext4_|ext4_fs_)", text
        ):
            return "file server process"
        if is_benchmark_comm(comm):
            if cpu_mode == "kernel":
                return "kernel"
            if stack_matches(frames, libfs_re):
                return "library file system"
            return "benchmark application"
        return f"other {cpu_mode}"

    return f"other {cpu_mode}"


def try_parse_perf_script_fields_sample_line(line: str):
    """
    Parse a single-line sample emitted with perf script -F/--fields output
    (comm pid tid cpu time event ip sym dso ...).

    Call-graph text may follow dso but classification uses top frame only.
    """
    stripped_line = line.strip()
    if not stripped_line:
        return None

    matched = FIELDS_SAMPLE_HEAD_RE.match(stripped_line)
    if not matched:
        return None

    groups = matched.groups()
    comm = groups[0]
    pid_int = int(groups[1])
    tid_int = int(groups[2])
    cpu_idx = int(groups[3])
    time_val = float(groups[4])
    event_name = groups[6].strip()
    rest = groups[7].strip()

    tokens = rest.split()
    if len(tokens) >= 3:
        ip_tok = tokens[0]
        dso_tok = tokens[-1]
        symbol_text = tokens[1] if len(tokens) == 3 else " ".join(tokens[1:-1])
        frames_payload = [
            {"ip": ip_tok, "symbol": symbol_text.strip(), "dso": dso_tok.strip()}
        ]
    elif len(tokens) == 2:
        frames_payload = [{"ip": tokens[0], "symbol": tokens[1].strip(), "dso": ""}]
    elif len(tokens) == 1:
        frames_payload = [{"ip": tokens[0], "symbol": "", "dso": ""}]
    else:
        return None

    period_val = int(groups[5]) if groups[5] is not None else 1

    return {
        "comm": comm.strip(),
        "pid": pid_int,
        "tid": tid_int,
        "cpu": cpu_idx,
        "time": time_val,
        "event": event_name,
        "period": period_val,
        "frames": frames_payload,
    }


def parse_perf_script(script_path):
    samples = []
    current = None

    with open(script_path, encoding="utf-8", errors="replace") as script_file:
        for line in script_file:
            if line.startswith("#"):
                continue

            script_fields_sample = try_parse_perf_script_fields_sample_line(line)
            if script_fields_sample is not None:
                if current is not None:
                    samples.append(current)
                    current = None
                samples.append(script_fields_sample)
                continue

            sample_match = SCRIPT_SAMPLE_RE.match(line)
            if sample_match:
                if current is not None:
                    samples.append(current)

                period = sample_match.group("period")
                current = {
                    "comm": sample_match.group("comm").strip(),
                    "pid": int(sample_match.group("pid")),
                    "tid": int(sample_match.group("tid") or sample_match.group("pid")),
                    "cpu": int(sample_match.group("cpu")),
                    "time": float(sample_match.group("time")),
                    "event": sample_match.group("event").strip(),
                    "period": int(period) if period else 1,
                    "frames": [],
                }
                continue

            if current is None:
                continue

            frame_match = STACK_FRAME_RE.match(line)
            if frame_match:
                current["frames"].append(
                    {
                        "ip": frame_match.group("ip"),
                        "symbol": (frame_match.group("symbol") or "").strip(),
                        "dso": (frame_match.group("dso") or "").strip(),
                    }
                )

    if current is not None:
        samples.append(current)

    return samples


def summarize_samples(
    samples, system, workload, iosize, app, libfs_re, journal_re, return_details=False
):
    groups = defaultdict(lambda: {"samples": 0, "weighted_samples": 0})
    details = defaultdict(lambda: {"samples": 0, "weighted_samples": 0})
    kept_weight = 0
    times = []

    for sample in samples:
        comm = sample["comm"]
        cpu_mode = parse_cpu_mode(sample["event"])
        component = classify_sample(
            system, comm, cpu_mode, sample["frames"], libfs_re, journal_re
        )
        if component is None:
            continue

        weight = sample["period"]
        groups[(component, cpu_mode)]["samples"] += 1
        groups[(component, cpu_mode)]["weighted_samples"] += weight
        frame = top_frame(sample["frames"])
        detail_key = (
            component,
            cpu_mode,
            comm,
            frame.get("symbol", "[unknown]"),
            frame.get("dso", "[unknown]"),
        )
        details[detail_key]["samples"] += 1
        details[detail_key]["weighted_samples"] += weight
        kept_weight += weight
        times.append(sample["time"])

    duration = max(times) - min(times) if len(times) >= 2 else 0.0
    rows = []
    for (component, cpu_mode), values in sorted(groups.items()):
        weighted_samples = values["weighted_samples"]
        rows.append(
            {
                "workload": workload,
                "iosize": iosize,
                "app": app,
                "component": component,
                "cpu_mode": cpu_mode,
                "samples": values["samples"],
                "weighted_samples": weighted_samples,
                "percent_of_kept_samples": (
                    round(weighted_samples / kept_weight * 100, 4)
                    if kept_weight
                    else 0.0
                ),
                "duration_sec": round(duration, 6),
                "samples_per_sec": (
                    round(weighted_samples / duration, 4) if duration > 0 else 0.0
                ),
            }
        )

    if not return_details:
        return rows

    detail_rows = []
    for (component, cpu_mode, comm, symbol, dso), values in sorted(
        details.items(),
        key=lambda item: item[1]["weighted_samples"],
        reverse=True,
    ):
        weighted_samples = values["weighted_samples"]
        detail_rows.append(
            {
                "workload": workload,
                "iosize": iosize,
                "app": app,
                "component": component,
                "cpu_mode": cpu_mode,
                "comm": comm,
                "top_symbol": symbol,
                "top_dso": dso,
                "samples": values["samples"],
                "weighted_samples": weighted_samples,
                "percent_of_kept_samples": (
                    round(weighted_samples / kept_weight * 100, 4)
                    if kept_weight
                    else 0.0
                ),
            }
        )

    return rows, detail_rows


def write_csv(rows, output_path):
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_detail_csv(rows, output_path):
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=DETAIL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def microbench_fs_tree_slug(cli_system: str):
    """Result-directory prefixes (microbench throughput log layout)."""
    if cli_system == "uFS":
        return "uFS"
    if cli_system == "oxbow":
        return "oxbow"
    if cli_system in ("ext4", "ext4-journal"):
        return "ext4"
    return None


def parse_perf_script_stem(script_stem: str):
    for perf_script_name_pattern in PERF_SCRIPT_NAME_PATTERNS:
        match = perf_script_name_pattern.match(script_stem)
        if match:
            return match.groups()
    return None


def append_script_path(found, script_path):
    if not script_path.is_file():
        return
    if not script_path.name.endswith(SCRIPT_SUFFIX):
        return
    filename = script_path.name
    stem = filename[: -len(SCRIPT_SUFFIX)]
    parsed_name = parse_perf_script_stem(stem)
    if not parsed_name:
        return
    wl, iosize_str, app_str = parsed_name
    found.append(
        (
            WORKLOAD_RANK.get(wl.lower(), 99),
            int(iosize_str),
            int(app_str),
            script_path,
            wl,
            int(iosize_str),
            int(app_str),
        )
    )


def collect_microbench_script_paths(batch_root: Path, filesystem_key: str):
    """
    Find exported microbench *.perf.script under result trees (same layout as
    microbench_performance_parse_breakdown.collect_perf_files). Supports both
    legacy perfthp_* trees and direct Throughput-* files in the perf root.
    """
    found = []
    if not batch_root.exists():
        return found

    for script_path in batch_root.iterdir():
        append_script_path(found, script_path)

    run_glob = f"{filesystem_key}_*_run_0"
    for run_dir in batch_root.rglob(run_glob):
        app_glob = f"log_{filesystem_key}_*_throughput_app_*"
        for app_dir in run_dir.rglob(app_glob):
            for script_path in app_dir.rglob("perfthp_*"):
                if script_path.parent.name != "perf":
                    continue
                append_script_path(found, script_path)

    found.sort()
    return found


def batch_parse_microbench_scripts(
    batch_root,
    cli_system_arg,
    libfs_pattern,
    journal_pattern,
    output_path,
):
    fs_slug_local = microbench_fs_tree_slug(cli_system_arg)
    if fs_slug_local is None:
        print(
            f"ERROR: --batch only supports filesystem tree uFS, oxbow, or ext4; "
            f"got --system={cli_system_arg!r}",
            file=sys.stderr,
        )
        write_csv([], output_path)
        return []

    libfs_compile = re.compile(libfs_pattern, re.IGNORECASE)
    journal_compile = re.compile(journal_pattern, re.IGNORECASE)
    classify_system_key = normalize_system(cli_system_arg)
    aggregated_rows = []
    scanned = collect_microbench_script_paths(batch_root, fs_slug_local)

    if not scanned:
        print(
            f"No '*{SCRIPT_SUFFIX}' files found under '{batch_root.resolve()}' "
            f"(expected: Throughput-*{SCRIPT_SUFFIX} directly under the perf root "
            f"or under .../log_{fs_slug_local}_*_throughput_app_*/**/perf/"
            f"perfthp_*{SCRIPT_SUFFIX}). "
            "Export scripts with microbench_perf_breakdown_parse.py first.",
            file=sys.stderr,
        )
        write_csv([], output_path)
        return aggregated_rows

    for (
        prio_wl,
        iosize_ord,
        _,
        script_path_obj,
        wl_raw,
        iosize_val,
        num_app_val,
    ) in scanned:
        _ = prio_wl, iosize_ord
        sample_list = parse_perf_script(script_path_obj)
        wl_display = normalize_workload(wl_raw)
        summarized = summarize_samples(
            sample_list,
            classify_system_key,
            wl_display,
            iosize_val,
            num_app_val,
            libfs_compile,
            journal_compile,
        )
        if not summarized and sample_list:
            print(
                f"WARNING: {script_path_obj.resolve()} had samples but produced "
                "no classified rows.",
                file=sys.stderr,
            )
        for row in summarized:
            row["_wl_rank"] = WORKLOAD_RANK.get(wl_raw.lower(), 99)
            aggregated_rows.append(row)

    aggregated_rows.sort(
        key=lambda row: (
            row["_wl_rank"],
            row["iosize"],
            row["app"],
            row["component"],
            row["cpu_mode"],
        )
    )

    for row in aggregated_rows:
        row.pop("_wl_rank", None)

    write_csv(aggregated_rows, output_path)
    return aggregated_rows


USAGE_EPILOG = """
Example — single .perf.script (summary + optional details):
  python3 microbench_parse_perf_script.py \\
    perfthp_seqwrite_iosize4096_1.perf.script \\
    --system oxbow \\
    --workload seqwrite \\
    --iosize 4096 \\
    --app 1 \\
    -o oxbow_seqwrite_4k_1_breakdown.csv \\
    --details-output oxbow_seqwrite_4k_1_details.csv

Example — batch scan (result tree with many perfthp_*.perf.script):
  python3 microbench_parse_perf_script.py \\
    --batch --batch-root ../DATA_microbench_ufs_latest/perf --system uFS
"""


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Summarize CPU usage breakdown from perf script (.perf.script export or "
            "classic perf script). Use --batch to scan microbench result directories."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=USAGE_EPILOG,
    )
    parser.add_argument(
        "script",
        nargs="?",
        type=Path,
        default=None,
        help="Path to perf script (.perf.script or perf script stdout)",
    )
    parser.add_argument(
        "--system",
        default="uFS",
        choices=["ext4", "ext4-journal", "uFS", "oxbow"],
        help="System represented by this perf script (default: uFS)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Scan --batch-root for microbench *.perf.script files",
    )
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=DEFAULT_PERF_ROOT,
        help=(
            "Root directory for --batch "
            "(default: current directory)"
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=(
            "Output CSV path "
            "(default: perf_script_breakdown.csv single-file mode; "
            "{system}_microbench_perf_script_breakdown.csv in --batch)"
        ),
    )
    parser.add_argument(
        "--details-output",
        type=Path,
        default=None,
        help=(
            "Optional detailed CSV grouped by component, cpu mode, comm, "
            "top symbol, and DSO. Single-file mode only."
        ),
    )
    parser.add_argument("--workload", default=None, help="Workload name (single file)")
    parser.add_argument(
        "--iosize", default=None, type=int, help="IO size (single file)"
    )
    parser.add_argument("--app", default=None, type=int, help="Clients (single file)")
    parser.add_argument(
        "--libfs-regex",
        default=DEFAULT_LIBFS_REGEX,
        help="Regex used to classify benchmark-process user stacks as library FS",
    )
    parser.add_argument(
        "--journal-regex",
        default=DEFAULT_JOURNAL_REGEX,
        help="Regex used to classify stacks as journaling work",
    )
    args = parser.parse_args()

    if args.batch:
        if args.script is not None:
            parser.error("do not pass SCRIPT when using --batch (use --batch-root only)")
        if args.details_output is not None:
            parser.error("--details-output is only for single-file mode (omit with --batch)")
        if args.workload is not None or args.iosize is not None or args.app is not None:
            parser.error(
                "--workload / --iosize / --app apply only to single-file mode (omit with --batch)"
            )
        out_path = (
            args.output
            if args.output is not None
            else Path(f"{args.system}_microbench_perf_script_breakdown.csv")
        )
        rows_merged = batch_parse_microbench_scripts(
            args.batch_root.resolve(),
            args.system,
            args.libfs_regex,
            args.journal_regex,
            out_path,
        )
        print(f"Batch root: {args.batch_root.resolve()}")
        print(
            f"Summary CSV merged {len(rows_merged)} row(s) written to {out_path.resolve()}"
        )
        return

    if args.script is None:
        parser.error("single-file mode requires a script path (positional argument)")
    if args.workload is None or args.iosize is None or args.app is None:
        parser.error("single-file mode requires --workload, --iosize, and --app")

    system = normalize_system(args.system)
    workload = normalize_workload(args.workload)
    libfs_re = re.compile(args.libfs_regex, re.IGNORECASE)
    journal_re = re.compile(args.journal_regex, re.IGNORECASE)

    out_single = (
        args.output if args.output is not None else Path("perf_script_breakdown.csv")
    )
    samples = parse_perf_script(args.script)
    print(f"Reading perf script from {args.script.resolve()}")
    summary_result = summarize_samples(
        samples,
        system,
        workload,
        args.iosize,
        args.app,
        libfs_re,
        journal_re,
        return_details=args.details_output is not None,
    )
    if args.details_output is not None:
        rows, detail_rows = summary_result
        write_detail_csv(detail_rows, args.details_output)
    else:
        rows = summary_result
    write_csv(rows, out_single)

    print(f"Parsed samples: {len(samples)}")
    print(f"Output rows: {len(rows)}")
    print(f"Summary CSV written to {out_single.resolve()}")
    if args.details_output is not None:
        print(
            f"Detail CSV ({len(detail_rows)} rows) written to "
            f"{args.details_output.resolve()}"
        )


if __name__ == "__main__":
    main()
