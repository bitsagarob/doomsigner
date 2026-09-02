#!/bin/sh
# Stage the game into the buildroot rootfs overlay, which becomes the image's
# filesystem. Only runtime code is copied: tests and packaging stay in boot-game/
# so they never ship to the device.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
source="$here/src/bootgame"
target="$here/../opt/rootfs-overlay/usr/local/bootgame/bootgame"

rm -rf "$target"
mkdir -p "$target"
(cd "$source" && find . -name '*.py') | while IFS= read -r rel; do
  mkdir -p "$target/$(dirname "$rel")"
  cp "$source/$rel" "$target/$rel"
done

echo "staged $(find "$target" -name '*.py' | wc -l) modules into ${target#"$here"/../}"
