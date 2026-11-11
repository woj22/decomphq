#!/usr/bin/env bash
# Rebuild everything: Blender models -> textures -> Godot import -> Android APK (apk/last-carriage.apk).
# Needs: pip install bpy fonttools pillow numpy; Godot 4.6 on PATH; Android SDK + export templates
# (run ../tools/build_apk.sh --setup once to install those).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/build_models.py
python3 tools/make_textures.py
godot --headless --path . --import >/dev/null 2>&1 || true
mkdir -p build apk
godot --headless --path . --export-debug "Android" build/last-carriage.apk
cp build/last-carriage.apk apk/last-carriage.apk
echo "OK: apk/last-carriage.apk ($(du -h apk/last-carriage.apk | cut -f1))"
