#!/bin/sh
# Stage the game into the buildroot rootfs overlay, which becomes the image's
# filesystem. Only runtime code is copied: tests and packaging stay in boot-game/
# so they never ship to the device.
#
# Run this before building an image. The overlay path is gitignored, so a fresh
# checkout has nothing there, and the build does not notice: it produced a
# working-looking image whose start.sh pointed at a package that was not in it.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
target="$here/../opt/rootfs-overlay/usr/local/bootgame/bootgame"

rm -rf "$target"
mkdir -p "$target/games"
cp "$here"/src/bootgame/*.py "$target"/
# The games are a subpackage, and catalog.py imports them by module path
# ("bootgame.games.snake"). Copying only the top level left the menu able to
# list a game it could not then load.
cp "$here"/src/bootgame/games/*.py "$target"/games/

# Staging that half-worked is what shipped last time, so check rather than
# assume. Every module the source tree has, the overlay must have.
missing=""
for source in $(cd "$here/src/bootgame" && find . -name '*.py'); do
    [ -f "$target/$source" ] || missing="$missing $source"
done
if [ -n "$missing" ]; then
    echo "stage.sh: these did not make it into the overlay:$missing" >&2
    exit 1
fi

echo "staged $(find "$target" -name '*.py' | wc -l | tr -d ' ') modules into ${target#"$here"/../}"
