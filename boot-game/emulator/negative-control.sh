#!/bin/sh
# Negative control for test-handoff.sh.
#
# Runs the game and sends no keys at all. The process must still be the game
# afterwards. If it has already handed off, the unlock is firing by itself and
# a passing handoff test proves nothing.
set -eu

Xvfb :99 -screen 0 800x600x24 >/tmp/xvfb.log 2>&1 &
sleep 2

cd /opt/src
PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot >/out/nc.log 2>&1 &
pid=$!
sleep 20

if ! kill -0 "$pid" 2>/dev/null; then
  echo "RESULT: process gone (crashed, or exec'd and then died)"
  grep -q "boot game failed" /out/nc.log && echo "  fallback DID fire" || echo "  fallback did not fire"
  exit 0
fi

cmdline=$(tr '\0' ' ' < /proc/$pid/cmdline)
echo "CMDLINE (no keys sent): $cmdline"
grep -q "boot game failed" /out/nc.log && echo "  fallback DID fire" || echo "  fallback did not fire"

case "$cmdline" in
  *bootgame.boot*) echo "CONTROL OK: still the game, so the handoff test is meaningful" ;;
  *)               echo "CONTROL FAILED: handed off with no input, handoff test is invalid" ;;
esac
