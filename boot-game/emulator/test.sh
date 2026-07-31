#!/bin/sh
# Stage a device-shaped tree, then run the boot game under the emulator in a
# container and assert the execv handoff actually happens.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
out=${OUT_DIR:-/tmp/emu-out}

"$here/run.sh"
mkdir -p "$out" && rm -f "$out"/*

# Runs as the invoking user so the staged tree stays writable afterwards, and
# with bytecode writes off so nothing is left behind in it at all.
exec sudo docker run --rm \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$here/.stage/opt":/opt \
  -v "$here/.stage/usr/local/bootgame":/usr/local/bootgame \
  -v "$here/test-handoff.sh":/test.sh:ro \
  -v "$out":/out \
  bootgame-emulator /test.sh
