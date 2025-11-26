#! /bin/bash
# This script has no assumption on the current working directory. Instead, it
# always find path based on the environment variables provided.

set -e  # exit if any fails
set -u  # all env vars must be set

function print_usage_and_exit() {
	echo "Usage: $0 [ ycsb-a | ycsb-b | ycsb-c | ycsb-d | ycsb-e | ycsb-f | all | a,b,c | ycsb-a,ycsb-c ] [ ufs | ext4 | ext4dj | oxbow ]"
	echo "  Specify which LevelDB workload to run on which filesystem"
	echo "    workload: 6 workloads available (shown above), run them all, or specify a comma-separated subset"
	echo "    ufs:  run uFS for given workload from 1 app to 10 apps"
	echo "    ext4: run ext4 for given workload from 1 app to 10 apps"
	echo "    ext4dj: run ext4dj for given workload from 1 app to 10 apps"
	exit 1
}

WORKLOAD_LIST=()

function parse_workloads() {
	local arg="$1"
	local IFS=','
	local -a tokens=()

	WORKLOAD_LIST=()

	read -ra tokens <<< "$arg"

	local token
	for token in "${tokens[@]}"; do
		local t="$token"

		# Remove all whitespace characters
		t="${t//[[:space:]]/}"
		if [ -z "$t" ]; then
			continue
		fi

		local workload
		if [[ "$t" == ycsb-* ]]; then
			workload="$t"
		else
			workload="ycsb-$t"
		fi

		case "$workload" in
			ycsb-a|ycsb-b|ycsb-c|ycsb-d|ycsb-e|ycsb-f)
				WORKLOAD_LIST+=("$workload")
				;;
			*)
				return 1
				;;
		esac
	done

	if [ ${#WORKLOAD_LIST[@]} -eq 0 ]; then
		return 1
	fi

	return 0
}

if [ ! $# = "2" ]; then print_usage_and_exit; fi
if [ "$1" != "all" ]; then
	if ! parse_workloads "$1"; then
		print_usage_and_exit
	fi
fi
if [ ! "$2" = "ufs" ] && [ ! "$2" = "ext4" ] && [ ! "$2" = "ext4dj" ] && [ ! "$2" = "oxbow" ]; then print_usage_and_exit; fi

# Finish checking, now execute
source "$AE_SCRIPT_DIR/common.sh"

# Go to destination to run
cd "$AE_BENCH_REPO_DIR/leveldb-1.22"

REUSE_DATA_DIR="/ssd-data/1"

# provide workload name as the first arguments
function run_one_workload_ufs() {
	workload=$1
	data_dir="$(mk-data-dir leveldb_${workload}_ufs)"
	echo "Run LevelDB: $workload"
	sudo -E python3 scripts/run_ldb_ufs.py "$workload" "$data_dir" "${@:2}"
}

function run_one_workload_ext4() {
	workload=$1
	fs_type=$2
	data_dir="$(mk-data-dir leveldb_${workload}_${fs_type})"
	echo "Run LevelDB: $workload"
	sudo -E python3 scripts/run_ldb_ext4.py --workload "$workload" --output-dir "$data_dir" --reuse-data-dir $REUSE_DATA_DIR "${@:3}"
}

function load_data_ext4() {
	fs_type=$1
	run_one_workload_ext4 fillseq "$fs_type" --num-app-only 10
}

function run_one_workload_oxbow() {
	workload=$1
	data_dir="$(mk-data-dir leveldb_${workload}_oxbow)"
	echo "Run LevelDB: $workload"
	sudo -E python3 scripts/run_ldb_oxbow.py "$workload" "$data_dir" "${@:2}"
}


# Running YCSB workload requires an existing LevelDB image, so we need to load
# the data into LevelDB first before running any YCSB workload
# For uFS: loading data is fast, so we mkfs to clear all the data and reload it
#     everytime before running YCSB workload
# For ext4: loading data is slow, so we only run loading once and back up the
#     image into /ssd-data/1/; everytime before running YCSB workload, we copy
#     the backup image into benchmarking directory i.e. /ssd-data/0/
# Thus, it is strongly preferred to run `all` instead of individual `ycsb-X`
# one-by-one, so that the script could resue the image
if [ "$2" = "ufs" ]; then
	# Setup device
	setup-spdk
	# Prep for spdk's config
	cleanup-ufs-config
	echo 'dev_name = "spdkSSD";' >> /tmp/spdk.conf
	echo 'core_mask = "0x2";' >> /tmp/spdk.conf
	echo 'shm_id = "9";' >> /tmp/spdk.conf

	# run_ldb_ufs would do load itself everytime
	if [ "$1" = "all" ]; then
		for job in 'a' 'b' 'c' 'd' 'e' 'f'
		do
			run_one_workload_ufs "ycsb-${job}"
		done
	else
		for workload in "${WORKLOAD_LIST[@]}"
		do
			run_one_workload_ufs "$workload"
		done
	fi
elif [ "$2" = "ext4" ] || [ "$2" = "ext4dj" ]; then
	# Make sure the device can be seen by the kernel
	reset-spdk
	if [ "$2" = "ext4dj" ]; then
		setup-ext4 1
	else
		setup-ext4 0
	fi

	sudo rm -rf "/ssd-data/0"
	sudo rm -rf "$REUSE_DATA_DIR"
	sudo mkdir -p "/ssd-data/0"
	sudo mkdir -p "$REUSE_DATA_DIR"

	### We disable lazy operations in ext4 mount.
	#
	# echo "===================================================================="
	# echo "Ext4 mount succeeds. However before further experiments, we will wait for $AE_EXT4_WAIT_AFTER_MOUNT seconds, because ext4's mount contains lazy operations, which would affect performance significantly. To ensure fair comparsion, we will resume experiments $AE_EXT4_WAIT_AFTER_MOUNT seconds later. Go grab a coffee!"
	# echo "===================================================================="
	# sleep $AE_EXT4_WAIT_AFTER_MOUNT
	# echo "Now we resumes..."

	if [ "$1" = "all" ]; then
		load_data_ext4 "$2"
		for job in 'a' 'b' 'c' 'd' 'e' 'f'
		do
			run_one_workload_ext4 "ycsb-${job}" "$2"
		done
	else
		load_data_ext4 "$2"
		for workload in "${WORKLOAD_LIST[@]}"
		do
			run_one_workload_ext4 "$workload" "$2"
		done
	fi

	# umount ext4
	reset-ext4
elif [ "$2" = "oxbow" ]; then
	if [ "$LDB_OXB_CREATE_SNAP" = "1" ]; then
		echo "Creating LevelDB snapshot..."

		run_one_workload_oxbow "ycsb-a" # Parameter does not matter.

		echo "LevelDB snapshot created. Done."
		exit 0 # Exit after creating a snapshot.

	elif [ "$1" = "all" ]; then
		for job in 'a' 'b' 'c' 'd' 'e' 'f'
		do
			run_one_workload_oxbow "ycsb-${job}"
		done
	else
		for workload in "${WORKLOAD_LIST[@]}"
		do
			run_one_workload_oxbow "$workload"
		done
	fi
fi
