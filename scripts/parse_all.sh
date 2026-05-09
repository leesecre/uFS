#!/bin/bash

function print_usage() {
	echo "Usage: $0 <bench> <filesystem> <result_dir>"
	echo "  <bench>       : micro | filebench | leveldb"
	echo "  <filesystem>  : ufs | oxbow | ext4 | ext4dj"
	echo "  <result_dir>  : result directory"
	exit 1
}

if [ $# -lt 3 ]; then
	echo "Error: Missing required arguments."
	print_usage
fi

BENCH=$1
FS_TYPE=$2
RESULT_DIR=$3


if [[ "$BENCH" == "micro" ]]; then
	if [[ "$FS_TYPE" == "oxbow" ]]; then
	(
		cd "$RESULT_DIR" || exit 1

		# perf result file is owned by root in default.
		sudo chown -R $USER:$USER .

		echo "################ THROUGHPUT #################################"
		python3 $BENCH_UFS/cfs_bench/exprs/oxbow_scripts/throughput_all_parse_2.py --system oxbow
		echo "################ LATENCY ####################################"
		python3 $BENCH_UFS/cfs_bench/exprs/oxbow_scripts/latency_all_parse.py --system oxbow
		echo "################ PERF (CPU USAGE) ###########################"
		# python3 $BENCH_UFS/cfs_bench/exprs/oxbow_scripts/microbench_performance_parse.py --system oxbow
		echo "---- perf.data: export .perf.script + comm/dso cycle CSV (breakdown) ----"
		python3 "$BENCH_UFS/cfs_bench/exprs/oxbow_scripts/microbench_performance_parse_breakdown.py" \
			--system oxbow --output-dir .
		echo "---- .perf.script: component breakdown (microbench_parse_perf_script --batch) ----"
		python3 "$BENCH_UFS/cfs_bench/exprs/oxbow_scripts/microbench_parse_perf_script.py" \
			--batch --batch-root . --system oxbow
	)
	elif [[ "$FS_TYPE" == "ext4" ]]; then
	(
		cd "$RESULT_DIR" || exit 1

		# perf result file is owned by root in default.
		sudo chown -R $USER:$USER .

		echo "################ THROUGHPUT #################################"
		python3 $BENCH_UFS/cfs_bench/exprs/oxbow_scripts/throughput_all_parse_2.py --system ext4
		echo "################ LATENCY ####################################"
		python3 $BENCH_UFS/cfs_bench/exprs/oxbow_scripts/latency_all_parse.py --system ext4
		echo "################ PERF (CPU USAGE) ###########################"
		# python3 $BENCH_UFS/cfs_bench/exprs/oxbow_scripts/microbench_performance_parse.py --system ext4
		echo "---- perf.data: export .perf.script + comm/dso cycle CSV (breakdown) ----"
		python3 "$BENCH_UFS/cfs_bench/exprs/oxbow_scripts/microbench_performance_parse_breakdown.py" \
			--system ext4 --output-dir .
		echo "---- .perf.script: component breakdown (microbench_parse_perf_script --batch) ----"
		python3 "$BENCH_UFS/cfs_bench/exprs/oxbow_scripts/microbench_parse_perf_script.py" \
			--batch --batch-root . --system ext4
	)
	elif [[ "$FS_TYPE" == "ufs" ]]; then
		echo "TODO"
	else
		echo "Error: Invalid filesystem name '$FS_TYPE'."
		print_usage
	fi

elif [[ "$BENCH" == "filebench" ]]; then
	(
		cd "$RESULT_DIR" || exit 1

		# Result files may be owned by root.
		sudo chown -R $USER:$USER .

		if [[ "$FS_TYPE" == "ufs" ]]; then
			# Original behavior: parse results in the current directory.
			echo "################ FILEBENCH THROUGHPUT (uFS) ################"
			python3 "$BENCH_UFS/oxbow-uFS_bench/filebench/scripts/parse_ufs_filebench_results.py"
			echo "################ FILEBENCH PERF (CPU USAGE, uFS) ###########"
			python3 "$BENCH_UFS/oxbow-uFS_bench/filebench/scripts/parse_ufs_filebench_perf.py"

			# Print generated summary files with full paths and contents.
			for f in "filebench_summary_all_sorted.csv" "cpu_usage_results.csv"; do
				if [[ -f "$f" ]]; then
					fullpath="$(readlink -f "$f")"
					echo "Generated file: $fullpath"
					echo "==================== $fullpath ===================="
					cat "$f"
					echo
				fi
			done
		elif [[ "$FS_TYPE" == "ext4" || "$FS_TYPE" == "ext4dj" || "$FS_TYPE" == "oxbow" ]]; then
			# New layout: RESULT_DIR may contain per-workload subdirectories such as
			#   DATA_filebench_varmail_${FS_TYPE}
			#   DATA_filebench_webserver_${FS_TYPE}
			# Parse all available workloads.
			workloads=("varmail" "webserver")
			any_found=0

			for wl in "${workloads[@]}"; do
				subdir="DATA_filebench_${wl}_${FS_TYPE}"
				if [[ -d "$subdir" ]]; then
					any_found=1
					echo "################ FILEBENCH THROUGHPUT (${FS_TYPE}, ${wl}) ################"
					(
						cd "$subdir" || exit 1
						python3 "$BENCH_UFS/oxbow-uFS_bench/filebench/scripts/parse_ufs_filebench_results.py"
						echo "################ FILEBENCH PERF (CPU USAGE, ${FS_TYPE}, ${wl}) ###########"
						python3 "$BENCH_UFS/oxbow-uFS_bench/filebench/scripts/parse_ufs_filebench_perf.py"

						# Print per-workload summary files with full paths and contents.
						for f in "filebench_summary_all_sorted.csv" "cpu_usage_results.csv"; do
							if [[ -f "$f" ]]; then
								fullpath="$(readlink -f "$f")"
								echo "Generated file: $fullpath"
								echo "==================== $fullpath ===================="
								cat "$f"
								echo
							fi
						done
					)
				fi
			done

			# Backward compatibility: if no per-workload subdirectories are found,
			# fall back to the original behavior of parsing the current directory.
			if [[ "$any_found" -eq 0 ]]; then
				echo "################ FILEBENCH THROUGHPUT (${FS_TYPE}) #####"
				python3 "$BENCH_UFS/oxbow-uFS_bench/filebench/scripts/parse_ufs_filebench_results.py"
				echo "################ FILEBENCH PERF (CPU USAGE, ${FS_TYPE}) #"
				python3 "$BENCH_UFS/oxbow-uFS_bench/filebench/scripts/parse_ufs_filebench_perf.py"

				for f in "filebench_summary_all_sorted.csv" "cpu_usage_results.csv"; do
					if [[ -f "$f" ]]; then
						fullpath="$(readlink -f "$f")"
						echo "Generated file: $fullpath"
						echo "==================== $fullpath ===================="
						cat "$f"
						echo
					fi
				done
			fi
		else
			echo "Error: filebench parsing for filesystem '$FS_TYPE' is not implemented."
			print_usage
		fi
	)
elif [[ "$BENCH" == "leveldb" ]]; then
	(
		cd "$RESULT_DIR" || exit 1

		# Result files may be owned by root.
		sudo chown -R $USER:$USER .

		python3 - << EOF
import sys
from pathlib import Path


def determine_num_ops(workload: str) -> int:
    if "fill" not in workload:
        return 100000
    elif "random" not in workload:
        return 10000000
    else:
        return 2000000


def parse_timer_latency(filepath: Path):
    try:
        with filepath.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[0] == "Timer" and parts[1] == "0:":
                    try:
                        return int(parts[2])
                    except ValueError:
                        continue
    except FileNotFoundError:
        return None
    return None


def compute_throughput_for(data_dir: Path, workload: str, num_app: int):
    num_ops = determine_num_ops(workload)
    base = data_dir / f"{workload}_num-app-{num_app}_leveldb"
    if not base.is_dir():
        return None

    total_tput = 0.0
    found_any = False

    for appid in range(1, num_app + 1):
        log_path = base / f"leveldb-{appid}.out"
        latency = parse_timer_latency(log_path)
        if latency is None or latency == 0:
            continue
        found_any = True
        total_tput += num_ops / latency * 1_000_000.0

    return total_tput if found_any else None


def main():
    base_dir = Path(".")

    workloads = [f"ycsb-{c}" for c in ["a", "b", "c", "d", "e", "f"]]
    target_system = "${FS_TYPE}"
    fs_label_map = {
        "ufs": "ufs-1",
        "ext4": "ext4-ordered",
        "ext4dj": "ext4-journal",
        "oxbow": "oxbow",
    }
    num_app_list = [1, 2, 4, 8]

    print("workloads,filesystem,app,ops/s")

    for workload in workloads:
        data_dir = base_dir / f"DATA_leveldb_{workload}_{target_system}"
        if not data_dir.is_dir():
            continue

        fs_label = fs_label_map.get(target_system, target_system)

        for num_app in num_app_list:
            tput = compute_throughput_for(data_dir, workload, num_app)
            if tput is None:
                continue

            tput_str = f"{tput:.3f}"
            print(f"{workload},{fs_label},{num_app},{tput_str}")


if __name__ == "__main__":
    main()
EOF
	)
else
	echo "Error: Invalid bench name '$BENCH'."
	print_usage
fi
