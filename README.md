## Get Started

### uFS
Build cfs first based on https://github.com/WiscADSL/uFS
Most of evaluation is reproduced by upper repository.
(TODO) uFS for oxbow workloads

### oxbow
Oxbow is compatible with POSIX, you can run ext4 also.
Only levelDB has different methods but it is for loading data.

## BUILD
DO NOT use artifcat_eval.sh directly in this BRANCH!

Run the script below, depending on the file system you want.
You can build each workload separately, but the default is to build the whole.
```
./scripts/cmpl_bench.sh oxbow
./scripts/cmpl_bench.sh ext4
./scripts/cmpl_bench.sh ufs
```

## HOW TO RUN
TODO:
### uFS
### oxbow
### ext4
