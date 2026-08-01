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
run_once() {
  sudo docker run --rm \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$here/.stage/opt":/opt \
  -v "$here/.stage/usr/local/bootgame":/usr/local/bootgame \
  -v "$here/test-handoff.sh":/test.sh:ro \
    -v "$out":/out \
    bootgame-emulator /test.sh
}

# The emulator's Tk thread is unreliable under Xvfb: it sometimes dies before
# binding <Key>, and then no keystroke ever reaches the game. That is a fault in
# the emulator, not in the game, but it makes this test flaky at roughly one
# failure in three. Retry rather than pretend, and say so when it happens.
attempt=1
while [ "$attempt" -le 3 ]; do
  echo "attempt $attempt/3"
  if run_once; then exit 0; fi
  echo "  attempt $attempt failed (emulator GUI thread is flaky), retrying"
  attempt=$((attempt + 1))
done

echo "FAILED after 3 attempts, this is more than emulator flakiness"
exit 1
