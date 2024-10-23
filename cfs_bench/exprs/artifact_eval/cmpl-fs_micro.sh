set -e  # exit if any fails
set -u  # all env vars must be set

function print_usage_and_exit() {
	echo "Usage: $0 [ ufs | ufsnj ]"
	echo "  Specify microbench to compile for"
	echo "    ufs:   uFS with global journaling (default of uFS)"
	echo "    ufsnj: uFS without journaling"
	exit 1
}

if [ ! $# = "1" ]; then print_usage_and_exit; fi
if [ ! "$1" = "ufs" ] && [ ! "$1" = "ufsnj" ]; then print_usage_and_exit; fi

source "$AE_SCRIPT_DIR/common.sh"

cd "$AE_REPO_DIR"

if [ "$1" = "ufs" ]; then
	cmpl-ufs
elif [ "$1" = "ufsnj" ]; then
	cmpl-ufs '-DCFS_JOURNAL_TYPE=NO_JOURNAL'
fi

export LIB_CFS='-lcfs'
export CFS_MACRO='-DCFS'

cd "$AE_BENCH_REPO"
cd FS_microbench
git checkout "$AE_UFS_FS_MICRO_BRANCH"
meson clean
./build.sh
