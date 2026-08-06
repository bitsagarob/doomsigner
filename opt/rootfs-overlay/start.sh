#!/bin/sh

cd /opt/src/

# --- black box recorder, off unless asked for --------------------------------
# This build has no console, and a cased device cannot be opened to reach the
# serial pins, so a failed boot is silent and unknowable. Writing what happened
# onto the FAT partition it booted from is the one channel that always exists:
# the card goes back in a laptop and the answer is sitting there.
#
# Only runs when a file called DEBUG is present on that partition. A signing
# device should not journal itself to removable storage by default, and nothing
# here is written unless someone deliberately asked. It records hardware and
# import failures only -- never seed material, which never reaches this script.
(
    mkdir -p /mnt/bootfs 2>/dev/null
    if mount -t vfat -o rw /dev/mmcblk0p1 /mnt/bootfs 2>/dev/null; then
        if [ -f /mnt/bootfs/DEBUG ]; then
            {
                echo "model:   $(tr -d '\000' < /proc/device-tree/model 2>/dev/null)"
                echo "kernel:  $(uname -srm)"
                echo "python:  $(/usr/bin/python3 -V 2>&1)"
                echo "profile: $(cat /etc/os-release 2>/dev/null | head -2 | tr '\n' ' ')"
                echo ""
                echo "imports the wallet needs:"
                for m in mnemonic periphery embit ecdsa PIL qrcode; do
                    if /usr/bin/python3 -c "import $m" 2>/dev/null; then
                        echo "  $m: ok"
                    else
                        echo "  $m: MISSING"
                    fi
                done
                echo ""
                # Leaf imports only. Importing seedsigner itself would touch the
                # display and buttons that the real wallet is starting on right
                # now, and two processes driving one panel is its own bug.
                echo "wallet modules:"
                /usr/bin/python3 -c "import seedsigner.models.seed" 2>&1 | tail -3
            } > /mnt/bootfs/BOOTLOG.TXT 2>&1
            sync
        fi
        umount /mnt/bootfs 2>/dev/null
    fi
) &


# On success the boot game execs into SeedSigner, so this process becomes the
# wallet. If it cannot even start, run the wallet directly instead: an image
# once shipped with the game staged nowhere, and because this line was the only
# thing launching anything, the device booted to a black screen. A signing
# device has to come up whatever the easter egg does.
#/usr/bin/python3 main.py >> /dev/kmsg 2>&1 &  # version that writes output to dmesg
{
    PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot ||
        /usr/bin/python3 main.py
} &

# Set the date to release so that GPG can work
TIME_DEFAULT_FILE="/opt/src/.build_commit_time"
TIME_FALLBACK="2025-02-28 12:00"
TIME_FILE="/mnt/microsd/time.txt"
TIME_VALUE="$TIME_FALLBACK"

if [ -f "$TIME_DEFAULT_FILE" ]; then
    TIME_FROM_DEFAULT=$(tr -d '\r\n' < "$TIME_DEFAULT_FILE")
    if [ -n "$TIME_FROM_DEFAULT" ]; then
        TIME_VALUE="$TIME_FROM_DEFAULT"
    fi
fi

if [ -f "$TIME_FILE" ]; then
    TIME_FROM_FILE=$(tr -d '\r\n' < "$TIME_FILE")
    if [ -n "$TIME_FROM_FILE" ]; then
        TIME_VALUE="$TIME_FROM_FILE"
    fi
fi

/bin/date -s "$TIME_VALUE" || /bin/date -s "$TIME_FALLBACK"
