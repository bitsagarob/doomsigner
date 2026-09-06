#!/usr/bin/env bash
# One command for a full Virtual HAT pass: every probe and every shooter,
# against whatever app source you point it at.
#
#   ./run_all.sh /home/rob/apps/seedsigner-sp/src        # dev
#   ./run_all.sh /home/rob/apps/_scratch/ss-card/src     # a branch worktree
#
# Existed because a "full test" was several hand-run scripts, which meant it was
# run less often than it should have been and slightly differently each time.
#
# Results land in a dated directory: the probes' output as text, and every
# screen as a numbered PNG. Picking which frames are worth publishing is still a
# human step; this gets you to the point of choosing.
set -uo pipefail

APP_SRC="${1:-/home/rob/apps/seedsigner-sp/src}"
UML="${UML_ROOT:-/home/rob/apps/_scratch/uml}"
RIG="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date -u +%Y%m%d-%H%M)"
OUT="$UML/out/pass-$STAMP"

[ -d "$APP_SRC/seedsigner" ] || { echo "no app source at $APP_SRC"; exit 1; }
[ -x "$UML/run.sh" ] || { echo "no UML sandbox at $UML (see README)"; exit 1; }

mkdir -p "$OUT"
echo "app source : $APP_SRC"
echo "results    : $OUT"
echo

# Stage the app and the fixtures the probes read.
STAGE="$UML/appsrc-pass"
rm -rf "$STAGE"; mkdir -p "$STAGE/tests/data"
cp -r "$APP_SRC/seedsigner" "$STAGE/"
for f in test_musig2_card.py test_musig2_psbt.py psbt_testing_util.py; do
  cp "$(dirname "$APP_SRC")/tests/$f" "$STAGE/tests/" 2>/dev/null || true
done
cp "$(dirname "$APP_SRC")/tests/data/musig2_psbts.json" "$STAGE/tests/data/" 2>/dev/null || true
mkdir -p "$STAGE/tests/data/psbt_test_suite"
cp "$(dirname "$APP_SRC")/tests/data/psbt_test_suite/NORMAL-1_p2wpkh.psbt" \
   "$STAGE/tests/data/psbt_test_suite/" 2>/dev/null || true
cp "$RIG"/*.py "$STAGE/"

run_one() {   # name, script inside /app, whether to capture the display
  local name="$1" script="$2" capture="${3:-yes}"
  local init="$UML/rootfs/pass-$name-init.sh"
  head -21 "$UML/rootfs/pytest-init.sh" \
    | sed "s|/uml/appsrc |/uml/appsrc-pass |" > "$init"
  {
    [ "$capture" = yes ] && echo "cat /dev/ss_spicap > /out/$name.bin &"
    echo "sleep 1"
    echo "cd /app && timeout 240 python3 /app/$script 2>&1 | grep -vE 'font load|Supersampl'"
    echo "sleep 1; sync"
    echo "echo o > /proc/sysrq-trigger"
    echo "sleep 3"
  } >> "$init"
  chmod +x "$init"

  echo "--- $name"
  timeout 600 "$UML/run.sh" "/pass-$name-init.sh" 2>&1 \
    | grep -vE "setup_one_line|ubd device|tempdir|^\s*$" > "$OUT/$name.txt"
  # The interesting lines are whatever the probe printed; the boot chatter is
  # not. Show the verdicts rather than the whole log.
  grep -vE "^(spidev|capture|crw|=== |Python 3)" "$OUT/$name.txt" \
    | grep -vE "^\s*$" | tail -14 | sed 's/^/    /' 

  if [ "$capture" = yes ] && [ -s "$UML/out/$name.bin" ]; then
    mkdir -p "$OUT/$name"
    python3 "$RIG/decode_st7789.py" "$UML/out/$name.bin" \
      "$OUT/$name/s.png" --split | tail -1
    mv "$UML/out/$name.bin" "$OUT/$name.bin"
  fi
  echo
}

run_one one-visit   card_one_visit_probe.py  no
run_one rounds      card_rounds_probe.py     no
run_one offer       shoot_card_offer.py      yes
run_one refusal     shoot_musig2_refusal.py  yes
run_one flow-musig2 "flow_walk.py musig2"    yes
run_one flow-normal "flow_walk.py normal"    yes

echo "screens:"
find "$OUT" -name 's-*.png' | wc -l
echo "everything in $OUT"
