#!/bin/bash

#ulimit -n 40960

sudo systemctl restart rshim
sleep 3
sudo ip addr add 192.168.200.3/24 dev tmfifo_net0
sudo ip addr add 192.168.14.117/24 dev enp175s0f1np1
sudo ip link set enp175s0f1np1 up

