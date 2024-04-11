#!/usr/bin/python3

import re
import csv

def parse_data(text):
    # Regular expressions to extract relevant information
    system_regex = r"opened file: (.+)"
    op_regex = r"thread \d+ start - file: .+"
    filesize_regex = r"opened file: .+"
    iosize_regex = r"# of ops: (\d+)"
    threadnum_regex = r"thread (\d+) start - file: .+"
    aggtput_regex = r"avg: (\d+\.\d+) msec"

    # Initialize variables to store parsed data
    system = ""
    op = ""
    filesize = ""
    iosize = ""
    threadnum = ""
    aggtput = ""

    # Parse each line of the text
    for line in text.split('\n'):
        # Extract system
        if "opened file:" in line:
            system = re.match(system_regex, line).group(1)
        # Extract op
        elif "thread" in line and "start - file:" in line:
            op = re.match(op_regex, line).group(1)
        # Extract filesize
        elif "opened file:" in line:
            filesize = re.match(filesize_regex, line).group(1)
        # Extract iosize
        elif "# of ops:" in line:
            iosize = re.match(iosize_regex, line).group(1)
        # Extract threadnum
        elif "thread" in line and "start - file:" in line:
            threadnum = re.match(threadnum_regex, line).group(1)
        # Extract aggtput
        elif "avg:" in line:
            aggtput = re.match(aggtput_regex, line).group(1)

            # Write parsed data to CSV file
            with open('parsed_data.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([system, op, filesize, iosize, threadnum, aggtput])

# Example usage
text = """
opened file: /ssd-data/testfile
thread 0 start - file: /ssd-data/testfile
# of ops: 131072
--------------- Aggregate Latency (Write + Fsync)
    count 131072
    avg: 0.065 msec (64.97 usec)
    min: 0.056 msec (55.82 usec)
    max: 3.221 msec (3220.90 usec)
    std: 0.036 msec (36.12 usec)
    50 percentile    : 0.060 msec (60.37 usec)
    99 percentile    : 0.076 msec (75.55 usec)
    99.9 percentile  : 0.732 msec (731.54 usec)
    99.99 percentile : 0.761 msec (761.47 usec)
    99.999 percentile: 2.934 msec (2933.91 usec)
    fsync-avg: 0.061 msec (61.35 usec)

CPU utilization recorded and saved to '/home/ahn9807/workspace/uFS-bench/FS_microbench/DATA_fs_micro_all_ext4_04-11-08-02-55/cpuutil_fsmicro_all_lat_sw_1K_128.out.csv'.
opened file: /ssd-data/testfile
thread 0 start - file: /ssd-data/testfile
# of ops: 32768
--------------- Aggregate Latency (Write + Fsync)
    count 32768
    avg: 0.075 msec (74.89 usec)
    min: 0.068 msec (67.73 usec)
    max: 2.628 msec (2628.26 usec)
    std: 0.039 msec (38.87 usec)
    50 percentile    : 0.073 msec (72.61 usec)
    99 percentile    : 0.080 msec (79.51 usec)
    99.9 percentile  : 0.753 msec (752.94 usec)
    99.99 percentile : 0.772 msec (772.15 usec)
    99.999 percentile: 2.628 msec (2628.26 usec)
    fsync-avg: 0.070 msec (70.06 usec)
"""

# Call the function to parse the text and generate CSV
parse_data(text)
