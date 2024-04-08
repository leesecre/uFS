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
                OUT_DIR = f"./results/tput/ext4_out_tput"
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
            OUT_DIR = f"./results/lat/ext4_out_lat"
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
        print("Usage: python script.py output_file")
        sys.exit(1)

    output_file = sys.argv[1]
    output_file = open(f"{output_file}/fs_micro_all_ext4.out", "w")
    
    run_micro_tput(output_file)
    
    output_file.close()

    print("Output files are in 'results' directory.")

