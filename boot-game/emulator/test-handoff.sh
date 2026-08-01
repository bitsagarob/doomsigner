#!/bin/sh
# Runs inside the container. Boots the game under Xvfb, drives the unlock
# sequence, and asserts the process actually exec'd into SeedSigner.
set -eu

Xvfb :99 -screen 0 800x600x24 >/tmp/xvfb.log 2>&1 &
sleep 2

cd /opt/src
PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot >/out/boot.log 2>&1 &
pid=$!

# The emulator opens a Tk window; give it time to appear and draw a few frames.
sleep 12

if ! kill -0 "$pid" 2>/dev/null; then
  echo "FAIL: boot game exited early"; tail -20 /out/boot.log; exit 1
fi

before=$(tr '\0' ' ' < /proc/$pid/cmdline)
echo "CMDLINE BEFORE: $before"
import -window root /out/emu-playing.png 2>/dev/null || true

xdotool search --onlyvisible --name "SeedSigner Emulator" windowactivate --sync 2>/dev/null || \
  xdotool search --name "SeedSigner Emulator" windowfocus 2>/dev/null || true
sleep 1

# steer once, then the unlock
xdotool key Up; sleep 0.5
import -window root /out/emu-steered.png 2>/dev/null || true
for k in 1 2 3; do xdotool key "$k"; sleep 0.6; done
sleep 6

if ! kill -0 "$pid" 2>/dev/null; then
  echo "FAIL: process died instead of exec'ing"; tail -30 /out/boot.log; exit 1
fi

after=$(tr '\0' ' ' < /proc/$pid/cmdline)
echo "CMDLINE AFTER:  $after"
import -window root /out/emu-after.png 2>/dev/null || true

# The crash fallback also ends up in main.py, so a bare cmdline check could
# pass for the wrong reason. Insist the game did not fail.
if grep -q "boot game failed" /out/boot.log; then
  echo "FAIL: handoff came from the crash fallback, not the unlock sequence"
  head -20 /out/boot.log
  exit 1
fi

case "$after" in
  *main.py*) echo "PASS: unlock sequence triggered the execv handoff" ;;
  *)         echo "FAIL: still running the game, no handoff"; tail -30 /out/boot.log; exit 1 ;;
esac
