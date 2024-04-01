#!/bin/bash -e

INSTALL_PATH=`dirname /mnt/disk.img`
UBUNTU_IMG_URL="https://releases.ubuntu.com/20.04.2/ubuntu-20.04.2-live-server-amd64.iso?_ga=2.267594445.2145028703.1615186104-1743255792.1615186104"
PCI_PASSTHROUGH="65:00.0"

QEMU_ARGS="-enable-kvm -s -cpu host -nographic -vnc localhost:2 -m 16G -smp 28 -drive format=raw,file=$INSTALL_PATH/disk.img,if=virtio,cache=none -net nic -net user,hostfwd=tcp::2223-:22 -device vfio-pci,host=$PCI_PASSTHROUGH"

mkdir -p $INSTALL_PATH

if ! test -f $INSTALL_PATH/"ubuntu.img"; then
	wget -O $INSTALL_PATH/ubuntu.img $UBUNTU_IMG_URL -P $INSTALL_PATH
fi;

if ! test -f $INSTALL_PATH/"disk.img"; then
	sudo apt install qemu-utils
	qemu-img create -f raw -o size=80G $INSTALL_PATH/disk.img
	QEMU_ARGS+=" -cdrom $INSTALL_PATH/ubuntu.img"
fi;

echo $QEMU_ARGS

sudo /bin/qemu-system-x86_64 $QEMU_ARGS
