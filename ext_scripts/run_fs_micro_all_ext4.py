#!/usr/bin/env python3
import os
import subprocess
import sys
import time

# Default configurations
BENCH_MICRO = "./"  # Set proper path.
OPS = ["sw", "sr", "rw", "rr"]
TOTAL_WRITE_SIZE = 1024
IO_SIZES = ["1K", "4K", "16K", "64K", "1M"]
NUM_THREADS = ["1"]
PINNING = "numactl -N 1 -m 1"
PINNING = ""

def drop_cache():
    subprocess.run(["sudo", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)

def run_micro_tput(output_dir):
    os.chdir(BENCH_MICRO)
    OPS=["sw"]
    TOTAL_WRITE_SIZE=40 * 1024
    IO_SIZES=["64K"]

    for OP in OPS:
        for IO_SIZE in IO_SIZES:
            for NUM_THREAD in NUM_THREADS:
                # Set file size.
                FILE_SIZE = TOTAL_WRITE_SIZE // int(NUM_THREAD)  # Round down.

                # Set output file path.
                OUT_DIR = f"{output_dir}/tput/ext4_out_tput"
                OUT_FILE = f"{OUT_DIR}/{OP}_{IO_SIZE}_{NUM_THREAD}t"
                OUT_CPU_FILE = f"{OUT_FILE}.cpu"
                os.makedirs(OUT_DIR, exist_ok=True)

                print("Dropping cache.")
                drop_cache()
            
                CMD = f"{PINNING} ./record_cpu_util.py {OUT_CPU_FILE} -- \"{BENCH_MICRO}build/tput_micro -d /ssd-data -s {OP} {FILE_SIZE}M {IO_SIZE} {NUM_THREAD}\""
                
                with open(f"{OUT_FILE}.out", "w") as out_file:
                    subprocess.run(f"echo Command: \"{CMD}\" | tee {OUT_FILE}.out", shell=True)
                    subprocess.run(f"{CMD} | tee -a {OUT_FILE}.out", shell=True)

def run_micro_lat(output_dir):
    ############# Overriding configurations #############
    TOTAL_WRITE_SIZE = 128
    #####################################################

    os.chdir(BENCH_MICRO)

    for OP in OPS:
        if OP == "sr" or OP == "rr":
            fd = os.open("/ssd-data/testfile", os.O_RDWR | os.O_CREAT)
            os.truncate(fd, TOTAL_WRITE_SIZE * 1024 * 1024)
            os.close(fd)

        for IO_SIZE in IO_SIZES:
            FILE_SIZE = TOTAL_WRITE_SIZE  # There is only 1 thread.

            # Set output file path.
            OUT_DIR = f"{output_dir}/lat/ext4_out_lat"
            OUT_FILE = f"{OUT_DIR}/{OP}_{IO_SIZE}"
            OUT_CPU_FILE = f"{OUT_FILE}.cpu"
            os.makedirs(OUT_DIR, exist_ok=True)

            print("Dropping cache.")
            drop_cache()

            CMD = f"{PINNING} ./record_cpu_util.py {OUT_CPU_FILE} -- \"{BENCH_MICRO}build/lat_micro -d /ssd-data -s {OP} {FILE_SIZE}M {IO_SIZE} 1\""

            with open(f"{OUT_FILE}.out", "w") as out_file:
                subprocess.run(f"echo Command: \"{CMD}\" | tee {OUT_FILE}.out", shell=True)
                subprocess.run(f"{CMD} | tee -a {OUT_FILE}.out", shell=True)

# Execute only if this script is directly executed. (Not imported)
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py output_dir")
        sys.exit(1)

    output_dir = sys.argv[1]
    
    run_micro_tput(output_dir)
    run_micro_lat(output_dir)

    print("Output files are in 'results' directory.")

