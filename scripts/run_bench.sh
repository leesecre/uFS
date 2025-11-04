#! /bin/bash
set -e

KFS_MOUNT_PATH="/ssd-data"

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

function run_microbench() {
  data_dir="$(mk-data-dir microbench_$1)"
  echo "${@:3} will be saved in $data_dir"

  cmd="python3 fsp_microbench_suite.py --fs "$1""
  cmd+=" --numapp=$2"
  cmd+=" --jobs=$UFSBENCH_WORKLOADS"
  cmd+=" ${@:3}"

  cd $BENCH_UFS/cfs_bench/exprs

  if [ "$1" = "ext4" ] || [ "$1" = "ext4nj" ] || [ "$1" = "ext4dj" ]; then
      reset-spdk
      sudo -E $cmd
      sudo mv $BENCH_UFS/ext4_*_run_0 "$data_dir"
  elif [ "$1" = "oxbow" ]; then
      sudo -E $cmd
      sudo mv $BENCH_UFS/oxbow_*_run_0 "$data_dir"
  fi
}

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
elif [[ "$BENCH" == "leveldb" ]]; then
  # Ensure leveldb is compiled
  source "$AE_SCRIPT_DIR/run-leveldb.sh"
  # Run leveldb
  run_leveldb "$FS_TYPE" "$BENCH"
else
  # Ensure microbench is compiled
  source "$AE_SCRIPT_DIR/run-microbench.sh"
  # Run microbench
fi
