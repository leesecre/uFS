#!/bin/bash

./init_eval.sh
#
# bash artifact_eval.sh cmpl filebench varmail ufs
# bash artifact_eval.sh run filebench varmail ufs
# bash artifact_eval.sh cmpl filebench varmail ext4
# bash artifact_eval.sh run filebench varmail ext4
# bash artifact_eval.sh cmpl filebench webserver ufs
# bash artifact_eval.sh run filebench webserver ufs
# bash artifact_eval.sh cmpl filebench webserver ext4
# bash artifact_eval.sh run filebench webserver ext4

bash artifact_eval.sh run fs_micro all ufs
bash artifact_eval.sh run fs_micro all ext4
