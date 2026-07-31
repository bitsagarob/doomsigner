#!/bin/sh
# Stage the game into the buildroot rootfs overlay, which becomes the image's
# filesystem. Only runtime code is copied: tests and packaging stay in boot-game/
# so they never ship to the device.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
target="$here/../opt/rootfs-overlay/usr/local/bootgame/bootgame"

rm -rf "$target"
mkdir -p "$target"
cp "$here"/src/bootgame/*.py "$target"/

echo "staged $(ls -1 "$target" | wc -l) modules into ${target#"$here"/../}"
