#!/usr/bin/env bash
# Rendered screenshot gallery: tools/screenshot.sh [WxH ...]  (default 1280x720). Output: game/tests/screenshots/<WxH>/
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GAME="$ROOT/game"
SIZES=("$@"); [ ${#SIZES[@]} -eq 0 ] && SIZES=(1280x720)
RC=0
for s in "${SIZES[@]}"; do
  w=${s%x*}; h=${s#*x}
  out="$GAME/tests/screenshots/$s"
  mkdir -p "$out"
  timeout 600 xvfb-run -a -s "-screen 0 ${w}x${h}x24" godot --path "$GAME" --rendering-driver opengl3 --resolution "${w}x${h}" \
    -- --playtest=res://tests/playthroughs/gallery.json --shots="$out" 2>&1 | grep -E "PLAYTEST|screenshot|FAIL" || RC=1
done
exit $RC
