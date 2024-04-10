#!/usr/bin/python3

import psutil
import csv
import time
import subprocess
import argparse


def record_cpu_utilization(program_name, program_args, file_name):
    start_time = time.time()

    file_path = f"{file_name}.csv"

    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = ['Elapsed Time (s)', 'CPU %']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Start the subprocess
        process = subprocess.Popen([program_name] + program_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        while process.poll() is None:  # Check if the process has terminated
            elapsed_time = round(time.time() - start_time, 2)  # Cut off to two decimal places
            cpu_percent = psutil.cpu_percent(interval=None)
            writer.writerow({'Elapsed Time (s)': elapsed_time, 'CPU %': cpu_percent})
            time.sleep(0.5)  # Sleep for 0.5 seconds

        # Read remaining output
        stdout, stderr = process.communicate()
        if stdout:
            print(stdout.decode())
        if stderr:
            print(stderr.decode())

    print(f"CPU utilization recorded and saved to '{file_name}.csv'.")


if __name__ == "__main__":
    # Accessing parsed arguments
    # Create argument parser
    parser = argparse.ArgumentParser(description="Record CPU utilization while running a program")

    # Add arguments
    parser.add_argument("output_filename", type=str, help="Filename to save CPU utilization data")
    parser.add_argument("program_name", type=str, help="Name of the program to run")
    parser.add_argument("program_args", nargs="*", type=str, help="Arguments for the program")

    # Parse arguments
    args = parser.parse_args()


    program_name = args.program_name
    program_args = args.program_args
    file_name = args.output_filename

    record_cpu_utilization(program_name, program_args, file_name)

