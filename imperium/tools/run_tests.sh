#!/usr/bin/env bash
# Imperium checks: import, headless smoke test (data references, navigation, population).
# Add --shots to also render the screenshot tour into tests/screenshots/.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
timeout 120 godot --headless --path "$ROOT" --import >/dev/null 2>&1 || true
out=$(timeout 300 godot --headless --path "$ROOT" -- --smoke 2>&1)
echo "$out" | grep -E "SMOKE|SCRIPT ERROR|ERROR: [^C]" 
echo "$out" | grep -q "SMOKE PASS" || { echo FAILURES; exit 1; }
if [ "${1:-}" = "--shots" ]; then "$ROOT/tools/screenshot.sh" || exit 1; fi
echo "ALL GREEN"
