## Install instructions

1, You have to install external applications required for the build filebench.
> sudo apt-get install flex autotools-dev automakea nlohmann-json-dev

2, Install g++-10, gcc-10, cmake-3.26 by following the guide.
> https://askubuntu.com/questions/1192955/how-to-install-g-10-on-ubuntu-18-04
> https://cmake.org/download/

3, Change to 'bash'. 'zsh' is not worked.
> git submodule init & git submodule update

4, Execute bash artifact_eval.sh and install all libraries in the artifact_eval.sh
> I made modification for building each libraries, so please ignore the "already exists"
kind of errors. Just use the pre-existing folders. 
> In folly, do not follow the artifact_eval.sh direction. Just go to the folly-20xx/_build and type 'make -j20'.
> After building spdk, copy libspdk.so to the /lib

5, cd cfsl mkdir build; cd build; cmake ..; make -j 20

6, Initialize the cpu utilization tracking using ./init_eval.sh
< Note that, to evaluate the filebench without cpu utilization, 
	you may need to re-initialize the uFS benchmarks.
