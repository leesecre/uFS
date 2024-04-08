#!/usr/bin/env python3
import os
import subprocess
import sys
import time

# REQUIRE:
# - current working directory is filebench/
# - environment variables "CFS_ROOT_DIR", "MKFS_SPDK_BIN", "CFS_MAIN_BIN_NAME"
CFS_ROOT_DIR = os.environ['CFS_ROOT_DIR']
MKFS_SPDK_BIN = os.environ['MKFS_SPDK_BIN']
CFS_MAIN_BIN_NAME = os.environ['CFS_MAIN_BIN_NAME']

# set up LD_LIBRARY_PATH
if "LD_LIBRARY_PATH" in os.environ:
    ld_lib_path = [os.environ["LD_LIBRARY_PATH"]]
else:
    ld_lib_path = []
ld_lib_path.append(f"{CFS_ROOT_DIR}/cfs/lib/tbb/build/tbb_build_release")
ld_lib_path.append(f"{CFS_ROOT_DIR}/cfs/build")
os.environ["LD_LIBRARY_PATH"] = ":".join(ld_lib_path)


def mkfs():
    # clear the data...
    subprocess.run([MKFS_SPDK_BIN, "mkfs"])
    time.sleep(1)

ready_fname = "/tmp/cfs_ready"
exit_fname = "/tmp/cfs_exit"
os.environ["READY_FILE_NAME"] = ready_fname

# Use same amount of workers and apps
def start_fsp(num_worker_app_pair, fsp_out):
    fsp_command = [CFS_MAIN_BIN_NAME]
    fsp_command.append(str(num_worker_app_pair))
    fsp_command.append(str(num_worker_app_pair + 1))
    offset_string = ""
    for j in range(0, num_worker_app_pair):
        offset_string += str(20 * j + 1)
        if j != num_worker_app_pair - 1:
            offset_string += ","
    fsp_command.append(offset_string)
    fsp_command.append(exit_fname)
    fsp_command.append("/tmp/spdk.conf")
    offset_string = ""
    for j in range(0, num_worker_app_pair):
        offset_string += str(j + 1)
        if j != num_worker_app_pair - 1:
            offset_string += ","
    fsp_command.append(offset_string)
    fsp_command.append("/tmp/fsp.conf")
    print(fsp_command)

    os.system(f"rm -rf {ready_fname}")
    os.system(f"rm -rf {exit_fname}")

    fs_proc = subprocess.Popen(fsp_command, stdout=fsp_out)
    while not os.path.exists(ready_fname):
        if fs_proc.poll() is not None:
            raise RuntimeError("uFS Server exits unexpectedly")
        time.sleep(0.1)
    return fs_proc


fsp_shutdown_timeout = 15
def shutdown_fsp(fs_proc):
    with open(exit_fname, 'w+') as f:
        f.write('Apparate')
    try:
        fs_proc.wait(fsp_shutdown_timeout)
        # if there is a large amount of data to flush before exits, it could
        # take a while before gracefully exit, but we don't really care...
        # to speed up the experiments, we just kill it...
    except subprocess.TimeoutExpired:
        print(f"WARN: uFS server doesn't exit after {fsp_shutdown_timeout} seconds; will enforce shutdown")
        subprocess.run(["pkill", "fsMain"])

# Default configurations
BENCH_MICRO = "./"  # Set proper path.
OPS = ["sw", "sr", "rw", "rr"]
TOTAL_WRITE_SIZE = 1024
IO_SIZES = ["1K", "4K", "16K", "64K", "1M"]
NUM_THREADS = ["1"]
PINNING = "numactl -N 1 -m 1"

def drop_cache():
    subprocess.run(["sudo", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)

def run_micro_tput(output_file):
    os.chdir(BENCH_MICRO)

    for OP in OPS:
        for IO_SIZE in IO_SIZES:
            for NUM_THREAD in NUM_THREADS:
                # Set file size.
                FILE_SIZE = TOTAL_WRITE_SIZE // int(NUM_THREAD)  # Round down.

                # Set output file path.
                OUT_DIR = f"./results/tput/ufs_out_tput"
                OUT_FILE = f"{OUT_DIR}/{OP}_{IO_SIZE}_{NUM_THREAD}t"
                os.makedirs(OUT_DIR, exist_ok=True)

                print("Dropping cache.")
                drop_cache()

            
                CMD = f"{PINNING} {BENCH_MICRO}build/tput_micro -d /ssd-data -s {OP} {FILE_SIZE}M {IO_SIZE} {NUM_THREAD}"
                
                # Print command.
                print("Command:", CMD)

                # Execute
                subprocess.run(CMD, shell=True, check=True, stdout=output_file, stderr=subprocess.PIPE)

def run_micro_lat(output_file):
    ############# Overriding configurations #############
    global TOTAL_WRITE_SIZE
    TOTAL_WRITE_SIZE = "128M"
    #####################################################

    os.chdir(BENCH_MICRO)

    for OP in OPS:
        for IO_SIZE in IO_SIZES:
            FILE_SIZE = TOTAL_WRITE_SIZE  # There is only 1 thread.

            # Set output file path.
            OUT_DIR = f"./results/lat/ufs_out_lat"
            OUT_FILE = f"{OUT_DIR}/{OP}_{IO_SIZE}"
            os.makedirs(OUT_DIR, exist_ok=True)

            print("Dropping cache.")
            drop_cache()

            CMD = f"{PINNING} {BENCH_MICRO}/build/lat_micro -d /ssd-data -s {OP} {FILE_SIZE}M {IO_SIZE} 1"

            # Print command.
            print("Command:", CMD)

            # Execute
            subprocess.run(CMD, shell=True, check=True, stdout=output_file, stderr=subprocess.PIPE)

# Execute only if this script is directly executed. (Not imported)
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py output_dir")
        sys.exit(1)

    output_file = sys.argv[1]
    output_file = open(f"{output_file}/fs_micro_all_ufs.out", "w")

    mkfs()

    fsp_out = open(f"{sys.argv[1]}/fs_micro_ufs.out", "w")
    fs_proc = start_fsp(1, fsp_out)

    run_micro_tput(output_file)

    shutdown_fsp(fs_proc)
    
    fsp_out.close()
    output_file.close()

    print("Output files are in 'results' directory.")

