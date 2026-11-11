#!/usr/bin/env bash
# Engine test pipeline: content validation -> scoring oracle -> headless unit tests -> playthroughs -> screenshots.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GAME="$ROOT/game"
FAIL=0
step() { echo; echo "=== $*"; }

godot --headless --path "$GAME" --import >/dev/null 2>&1 || true

if [ -f "$ROOT/tools/validate_content.py" ]; then
  step "content validation"
  python3 "$ROOT/tools/validate_content.py" || FAIL=1
fi
if [ -f "$ROOT/tools/scoring_ref.py" ]; then
  step "scoring oracle (tools/scoring_ref.py)"
  python3 "$ROOT/tools/scoring_ref.py" || FAIL=1
fi

step "headless unit tests"
timeout 600 godot --headless --path "$GAME" -s res://tests/run_tests.gd 2>&1 | grep -E "^  (ok|FAIL)|UNIT TESTS|SCRIPT ERROR" || true
timeout 600 godot --headless --path "$GAME" -s res://tests/run_tests.gd >/dev/null 2>&1 || FAIL=1

step "scripted playthroughs (PROJECT §10.8)"
for p in perfect attentive half_diligent rubric_only careless; do
  out=$(timeout 600 godot --headless --path "$GAME" -- --playtest=res://tests/playthroughs/$p.json 2>&1)
  echo "$out" | grep -E "PLAYTEST|FAIL" || { echo "PLAYTEST $p.json: no result"; FAIL=1; }
  echo "$out" | grep -q "PASS" || FAIL=1
done

if [ "${SKIP_SHOTS:-0}" != "1" ]; then
  step "screenshots"
  "$ROOT/tools/screenshot.sh" || FAIL=1
fi

echo
[ $FAIL -eq 0 ] && echo "ALL GREEN" || echo "FAILURES"
exit $FAIL
