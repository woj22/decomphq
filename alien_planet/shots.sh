#!/usr/bin/env bash
# Render the screenshot gallery: alien_planet/shots.sh OUTDIR [WxH] [--touch]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?out dir}"; RES="${2:-1280x720}"; shift; shift || true; EXTRA="$*"
W=${RES%x*}; H=${RES#*x}
godot --headless --path "$HERE/godot" --import >/dev/null 2>&1 || true
timeout 600 xvfb-run -a -s "-screen 0 ${W}x${H}x24" godot --path "$HERE/godot" --rendering-driver opengl3 \
  --resolution "$RES" -- --shots="$OUT" $EXTRA 2>&1 | grep -E "SHOT|ERROR|SCRIPT" || true
