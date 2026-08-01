# Runs the boot game against the desktop SeedSigner emulator, headless.
#
# The layout mirrors the device on purpose: the app at /opt/src, the game at
# /usr/local/bootgame, and a /usr/bin/python3 for os.execv to find. That way the
# exact command line from opt/rootfs-overlay/start.sh is what gets exercised.
FROM python:3.12

RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb xdotool imagemagick libzbar0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        pillow embit urtypes qrcode mock pyzbar opencv-python-headless

# SeedSigner's boot script invokes /usr/bin/python3 explicitly.
RUN ln -sf /usr/local/bin/python3 /usr/bin/python3

ENV DISPLAY=:99
