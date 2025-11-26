#! /bin/bash
set -e

## Argument checking
if [ $# -lt 2 ]; then
  echo "Error: Missing required arguments."
  print_usage
fi

BENCH=$1
FS_TYPE=$2

if [[ "$BENCH" != "microbench" && "$BENCH" != "filebench" && "$BENCH" != "leveldb" ]]; then
  echo "Error: Invalid bench name '$BENCH'."
  print_usage
fi

if [[ "$FS_TYPE" != "oxbow" && "$FS_TYPE" != "ext4" && "$FS_TYPE" != "ext4nj" && "$FS_TYPE" != "ext4dj" ]]; then
  echo "Error: Invalid filesystem name '$FS_TYPE'."
  print_usage
fi

if [[ "$FS_TYPE" == "ext4" || "$FS_TYPE" == "ext4nj" || "$FS_TYPE" == "ext4dj" ]]; then
  # Use NVME_DEV_NAME_EXT4 when available; otherwise keep existing NVME_DEV_NAME.
  export NVME_DEV_NAME="${NVME_DEV_NAME_EXT4:-$NVME_DEV_NAME}"
else
  export NVME_DEV_NAME="$NVME_DEV_NAME"
fi
echo "NVMe device name: $NVME_DEV_NAME"

export AE_SSD_NAME="$NVME_DEV_NAME"

## Required for running microbench and leveldb.
export KFS_MOUNT_PATH="/ssd-data"

## Required for running leveldb.
export CFS_ROOT_DIR="$BENCH_UFS"
export AE_REPO_DIR="$BENCH_UFS"
# export AE_WORK_DIR="$BENCH_UFS"
export AE_SCRIPT_DIR="$BENCH_UFS/cfs_bench/exprs/artifact_eval"
export AE_BENCH_REPO_DIR="$BENCH_UFS/oxbow-uFS_bench"
export AE_EXT4_WAIT_AFTER_MOUNT='15'  # unit is second
export AE_DATA_DIR="${BENCH_UFS}/DATA"
export OXBOW_LEVELDB_SNAPSHOT_FILE_PATH="${BENCH_UFS}/leveldb_oxbow_snapshot.img"

# Oxbow status directory path. Must be same with EXP_FLAG_DIR in oxbow/devfs/include/common/oxbow.h
export EXP_FLAG_DIR="${EXP_FLAG_DIR:-/mnt/oxbow_flag}"

# Do not set both at the same time. (Cf. run_ldb_oxbow.py)
export LDB_OXB_CREATE_SNAP="${LDB_OXB_CREATE_SNAP:-0}" # Create a snapshot of db.
export LDB_OXB_LOAD_SNAP="${LDB_OXB_LOAD_SNAP:-0}" # Use a snapshot instead of filling db.

if [ -z "$OXBOW_ENV_SOURCED" ]; then
	echo "Do source set_env.sh first. in oxbow root directory"
	exit
fi

function print_usage() {
  echo "Usage: $0 <bench> <filesystem>"
  echo "  <bench>       : microbench | filebench | leveldb"
  echo "  <filesystem>  : ufs | oxbow | ext4 | ext4nj | ext4dj"
  exit 1
}

function reset-spdk() {
	DEV_NAME="/dev/$NVME_DEV_NAME"
	if sudo grep -qF "$DEV_NAME $KFS_MOUNT_PATH" /proc/mounts ; then
		echo "Detect $DEV_NAME has already mounted on $KFS_MOUNT_PATH"
		sudo umount "$KFS_MOUNT_PATH"
    if [ $? -ne 0 ]; then
      echo "Failed to unmount $DEV_NAME from $KFS_MOUNT_PATH"
      echo "Please check if the device is busy or mounted elsewhere."
      exit 1
    fi
	fi
	sudo bash $BENCH_UFS/cfs/lib/spdk/scripts/setup.sh reset
}

function mk-data-dir() {
	if [ ! $# = "1" ]; then
		echo "Usage: mk-data-dir exper_name" >&2
		exit 1
	fi
  mkdir -p "$BENCH_UFS/DATA"
	exper_name="$1"
	data_dir="$BENCH_UFS/DATA/${exper_name}_$(date +%m-%d-%H-%M-%S)"
	mkdir "$data_dir"
	echo "$data_dir"
}

function collect_leveldb_data() {
	# Collect LevelDB experiment data for a given filesystem into a single
	# timestamped directory under $AE_DATA_DIR.
	local fs_system="$1"

	# Artifact-eval scripts use "ufs", "ext4", "ext4dj", "oxbow" in
	# DATA_leveldb_*_<fs> directory names.
	local src_fs="$fs_system"
	if [[ "$src_fs" == "ext4nj" ]]; then
		src_fs="ext4"
	fi

	if [ -z "${AE_DATA_DIR:-}" ]; then
		echo "AE_DATA_DIR is not set; skip LevelDB data collection."
		return
	fi

	mkdir -p "$AE_DATA_DIR"

	local ts
	if [ -n "${LEVELDB_BENCH_TS:-}" ]; then
		ts="$LEVELDB_BENCH_TS"
	else
		ts=$(date +%m-%d-%H-%M-%S)
	fi
	local dest_dir="$AE_DATA_DIR/leveldb_${src_fs}_${ts}"
	mkdir -p "$dest_dir"

	local found_any="false"

	for src_link in "$AE_DATA_DIR"/DATA_leveldb_*_"$src_fs"; do
		if [ ! -e "$src_link" ]; then
			continue
		fi

		found_any="true"

		local base
		base=$(basename "$src_link")

		# Resolve real path in case it is a symlink.
		local real_path
		real_path=$(readlink -f "$src_link" 2>/dev/null || echo "")
		if [ -z "$real_path" ] || [ ! -d "$real_path" ]; then
			continue
		fi

		local dst="$dest_dir/$base"
		mkdir -p "$dst"

		# Ensure we can read all files in the source directory (perf.data are root-owned).
		# Make them world-readable before copying.
		sudo chmod -R a+r "$real_path"

		# Copy all contents from the real data directory.
		cp -a "$real_path"/. "$dst"/

		# Normalize permissions of collected directories and files.
		# Directories: 755, Files: 644.
		find "$dst" -type d -exec chmod 755 {} +
		find "$dst" -type f -exec chmod 644 {} +
	done

	if [[ "$found_any" == "false" ]]; then
		echo "No LevelDB data directories found for filesystem '$src_fs' under $AE_DATA_DIR."
		rmdir "$dest_dir" 2>/dev/null || true
	else
		echo "LevelDB results collected under: $dest_dir"
	fi
}

function collect_filebench_data() {
	# Collect filebench experiment data for a given filesystem into a single
	# timestamped directory under $AE_DATA_DIR.
	local fs_system="$1"

	# Artifact-eval scripts use "ufs", "ext4", "ext4dj", "oxbow" in
	# DATA_filebench_*_<fs> directory names.
	local src_fs="$fs_system"
	if [[ "$src_fs" == "ext4nj" ]]; then
		src_fs="ext4"
	fi

	if [ -z "${AE_DATA_DIR:-}" ]; then
		echo "AE_DATA_DIR is not set; skip filebench data collection."
		return
	fi

	mkdir -p "$AE_DATA_DIR"

	local ts
	if [ -n "${FILEBENCH_BENCH_TS:-}" ]; then
		ts="$FILEBENCH_BENCH_TS"
	else
		ts=$(date +%m-%d-%H-%M-%S)
	fi
	local dest_dir="$AE_DATA_DIR/filebench_${src_fs}_${ts}"
	mkdir -p "$dest_dir"

	local found_any="false"

	for src_link in "$AE_DATA_DIR"/DATA_filebench_*_"$src_fs"; do
		if [ ! -e "$src_link" ]; then
			continue
		fi

		found_any="true"

		local base
		base=$(basename "$src_link")

		# Resolve real path in case it is a symlink.
		local real_path
		real_path=$(readlink -f "$src_link" 2>/dev/null || echo "")
		if [ -z "$real_path" ] || [ ! -d "$real_path" ]; then
			continue
		fi

		local dst="$dest_dir/$base"
		mkdir -p "$dst"

		# Ensure we can read all files in the source directory (perf.data are root-owned).
		# Make them world-readable before copying.
		sudo chmod -R a+r "$real_path"

		# Copy all contents from the real data directory.
		cp -a "$real_path"/. "$dst"/

		# Normalize permissions of collected directories and files.
		# Directories: 755, Files: 644.
		find "$dst" -type d -exec chmod 755 {} +
		find "$dst" -type f -exec chmod 644 {} +
	done

	if [[ "$found_any" == "false" ]]; then
		echo "No filebench data directories found for filesystem '$src_fs' under $AE_DATA_DIR."
		rmdir "$dest_dir" 2>/dev/null || true
	else
		echo "filebench results collected under: $dest_dir"
	fi
}

function run_microbench() {
  data_dir="$(mk-data-dir microbench_$1)"
  echo "Results will be saved in $data_dir"

  cd "$BENCH_UFS/cfs_bench/exprs"

  cmd=(python3 fsp_microbench_suite.py --fs "$1")
  cmd+=(--numapp="$UFSBENCH_NUMAPP")
  cmd+=(--jobs="$UFSBENCH_WORKLOADS")
  cmd+=("${@:3}")

  if [ "$1" = "ext4" ] || [ "$1" = "ext4nj" ] || [ "$1" = "ext4dj" ]; then
      reset-spdk
      sudo -E "${cmd[@]}"
      sudo mv "$BENCH_UFS"/ext4_*_run_0 "$data_dir"
  elif [ "$1" = "oxbow" ]; then
      sudo -E "${cmd[@]}"
      sudo mv "$BENCH_UFS"/oxbow_*_run_0 "$data_dir"
  fi
}

echo "Running benchmark: $BENCH with filesystem: $FS_TYPE"
source "$BENCH_UFS/scripts/config.sh"

echo "Perform some pre-run cleaning: it may report some errors for files/processes not found, but it should be fine..."
set +e  # allow non-zero return value for file/process not found
sudo killall fsMain
sudo killall cfs_bench
sudo killall cfs_bench_coordinator
sudo killall testRWFsUtil
sudo rm -rf "$BENCH_UFS"/log*
sudo rm -rf "$BENCH_UFS"/*_run_*
sudo rm -rf "/dev/shm/coordinator"

if [[ "$BENCH" == "microbench" ]]; then
  run_microbench "$FS_TYPE"

elif [[ "$BENCH" == "filebench" ]]; then
  if [[ "$FS_TYPE" == "ext4nj" ]]; then
    echo "Error: filebench benchmark does not support filesystem 'ext4nj'."
    echo "Supported filesystems for filebench: oxbow, ext4, ext4dj."
    exit 1

  elif [[ "$FS_TYPE" == "oxbow" ]]; then
    echo "Increasing max map count to 1000000 for Oxbow..."
    sudo sysctl -w vm.max_map_count=1000000
    cat /proc/sys/vm/max_map_count
  fi

  # Clean up existing filebench latest links for this filesystem to avoid
  # mixing data from previous runs. Artifact-eval scripts use "ufs", "ext4",
  # "ext4dj", "oxbow" in DATA_filebench_*_<fs> directory names.
  if [ -n "${AE_DATA_DIR:-}" ]; then
    src_fs="$FS_TYPE"
    if [[ "$src_fs" == "ext4nj" ]]; then
      echo "Error: filebench benchmark does not support filesystem 'ext4nj'."
      exit 1
    fi

    for old_link in "$AE_DATA_DIR"/DATA_filebench_*_"$src_fs"; do
      if [ ! -e "$old_link" ]; then
        continue
      fi
      sudo rm -rf "$old_link"
    done
  fi

  FILEBENCH_BENCH_TS=$(date +%m-%d-%H-%M-%S)

  workloads="${FILEBENCH_WORKLOAD:-varmail,webserver}"
  echo "Running filebench workloads (${workloads}) on filesystem: $FS_TYPE"
  for workload in $(echo "$workloads" | tr ',' ' '); do
    echo "Running filebench workload: $workload"
    sudo -E "$AE_SCRIPT_DIR/run-filebench.sh" "$workload" "$FS_TYPE"
  done

  # After running filebench workloads, collect all DATA_filebench_*_<fs>
  # entries into a single timestamped directory for convenience.
  collect_filebench_data "$FS_TYPE"

elif [[ "$BENCH" == "leveldb" ]]; then

  # Clean up existing LevelDB latest links for this filesystem to avoid mixing
  # data from previous runs. Artifact-eval scripts use "ufs", "ext4",
  # "ext4dj", "oxbow" in DATA_leveldb_*_<fs> directory names.
  if [ -n "${AE_DATA_DIR:-}" ]; then
    src_fs="$FS_TYPE"
    if [[ "$src_fs" == "ext4nj" ]]; then
      src_fs="ext4"
    fi

    for old_link in "$AE_DATA_DIR"/DATA_leveldb_*_"$src_fs"; do
      if [ ! -e "$old_link" ]; then
        continue
      fi
      sudo rm -rf "$old_link"
    done
  fi

  LEVELDB_BENCH_TS=$(date +%m-%d-%H-%M-%S)

  # Ensure leveldb is compiled
  sudo -E "$AE_SCRIPT_DIR/run-leveldb.sh" "$LEVELDB_WORKLOAD" "$FS_TYPE"

  # After running LevelDB workloads, collect all DATA_leveldb_*_<fs> entries
  # into a single timestamped directory for convenience.
  collect_leveldb_data "$FS_TYPE"
fi
