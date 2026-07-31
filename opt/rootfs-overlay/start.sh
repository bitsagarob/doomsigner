#!/bin/sh

cd /opt/src/

#/usr/bin/python3 main.py >> /dev/kmsg 2>&1 &  # version that writes output to dmesg
PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot &
