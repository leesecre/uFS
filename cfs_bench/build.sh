#!/bin/bash

rm -rf build
mkdir build
cd build
cmake .. -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DENABLE_DUMPLOAD=OFF # Disable logging.
# cmake .. -DCMAKE_EXPORT_COMPILE_COMMANDS=1
make -j
