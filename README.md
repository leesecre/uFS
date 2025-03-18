# uFS-bench for oxbow

Utilize microbench of uFS to evaluate oxbow file system.
We don't require cfs to be build, only cfs_bench required.

## Get Started

We have tested uFS on Ubuntu 20.04 LTS and Ubuntu 18.04 LTS (both with Linux 5.4). We use `c++20`, `gcc-10`, and `g++-10`. uFS relies on
the user-level NVMe driver provided by SPDK and the version (18.04) is embeded in this repo.

### Download and Build

Please check this [section](https://github.com/WiscADSL/uFS/tree/main/cfs_bench/exprs/artifact_eval#initialization) in artifact evalution document to *setup the environments* and *install necessary dependencies*.
DO NOT use artifcat_eval.sh directly in this BRANCH!
You may install config4cpp as the script do, and tbb can be build by sudo apt-get install libtbb-dev

Then to build uFS-bench, try these:
```
# assume all the dependencies have been installed by artifact_eval.sh
cd cfs_bench
mkdir build && cd build
cmake ..
make -j $(proc)              # proc: set it according to core number
```

### Setting

Checking set_env.sh in oxbow root directory and check env variables are proper.
You may put some proper values for running the uFS-bench.

### Running

After you starting daemon and devfs, try these to run uFS-bench:
```
cd bench/uFS/cfs_bench/exprs/artifact_eval
./artifact_eval.sh run microbench oxbow
```

You can change benchmark on fsp_microbench_suite.py.
Check each benchmark related python file on get_benchmark_script().
