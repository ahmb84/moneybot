#!/bin/sh
set -ex
DEVICE=/dev/xvdh
while [ ! -e "${DEVICE}" ]; do
    sleep 5
done
mkfs.ext4 "${DEVICE}"
shutdown -h now
