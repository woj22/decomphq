#!/usr/bin/env bash
# Renders the screenshot tour (rooms, conversations, court roster, overview) into tests/screenshots/<WxH>/.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIZES=("$@"); [ ${#SIZES[@]} -eq 0 ] && SIZES=(1280x720)
RC=0
for s in "${SIZES[@]}"; do
  w=${s%x*}; h=${s#*x}
  out="$ROOT/tests/screenshots/$s"
  mkdir -p "$out"
  timeout 600 xvfb-run -a -s "-screen 0 ${w}x${h}x24" godot --path "$ROOT" --rendering-driver opengl3 --resolution "${w}x${h}" \
    -- --shots="$out" 2>&1 | grep -E "screenshot|SCRIPT ERROR" || RC=1
done
exit $RC
