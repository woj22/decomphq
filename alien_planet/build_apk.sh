#!/usr/bin/env bash
# Debug-signed, sideloadable Android APK of the prototype.
# Prerequisites (Android SDK, Godot 4.6 export templates, debug keystore): run tools/build_apk.sh --setup once.
# Output: dist/alien-planet-debug.apk
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/dist"
cd "$ROOT/alien_planet/godot"
godot --headless --path . --import >/dev/null 2>&1 || true
godot --headless --path . --export-debug "Android" "$ROOT/dist/alien-planet-debug.apk" 2>&1 | grep -iE "error" | grep -viE "alsa|audio" || true
test -s "$ROOT/dist/alien-planet-debug.apk"
/opt/android-sdk/build-tools/35.0.1/apksigner verify "$ROOT/dist/alien-planet-debug.apk" && echo "OK: dist/alien-planet-debug.apk ($(du -h "$ROOT/dist/alien-planet-debug.apk" | cut -f1))"
