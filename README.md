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
(If build errors with -ltbb -> $ sudo apt-get install libtbb-dev)

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

## LevelDB

### How to enable sanitizer
1. Build libfs with sanitizer flag. (`oxbow/libfs/meson.build`)
2. Build leveldb with sanitizer flag. Set `SANITIZE=1` in `scripts/cmpl_bench.sh`.
3. Run with env `ASAN_LIB`. Set `ASAN_LIB` in `scripts/config.sh`.

