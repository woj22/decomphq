#!/usr/bin/env bash
# Build a debug-signed, sideloadable Android APK of the game.
# Usage: tools/build_apk.sh [--setup]   (--setup installs SDK/templates/keystore first; idempotent)
# Output: dist/purgatory-border-debug.apk
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT_VER="4.6"
SDK=/opt/android-sdk
KEYS=/opt/android-keys/debug.keystore
TPL="$HOME/.local/share/godot/export_templates/${GODOT_VER}.stable"
ES="$HOME/.config/godot/editor_settings-${GODOT_VER}.tres"
JAVA_HOME_GUESS=$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")

setup() {
  if [ ! -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
    mkdir -p "$SDK/cmdline-tools" && cd "$SDK"
    curl -sSL -o clt.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
    unzip -q clt.zip -d cmdline-tools && mv cmdline-tools/cmdline-tools cmdline-tools/latest && rm clt.zip
  fi
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null || true
  "$SDK/cmdline-tools/latest/bin/sdkmanager" "platform-tools" "build-tools;35.0.1" "platforms;android-35" >/dev/null
  if [ ! -f "$TPL/android_debug.apk" ]; then
    mkdir -p "$(dirname "$TPL")" && cd "$(dirname "$TPL")"
    curl -sSL -o t.tpz "https://github.com/godotengine/godot/releases/download/${GODOT_VER}-stable/Godot_v${GODOT_VER}-stable_export_templates.tpz"
    unzip -q t.tpz && rm -rf "${GODOT_VER}.stable" && mv templates "${GODOT_VER}.stable" && rm t.tpz
  fi
  if [ ! -f "$KEYS" ]; then
    mkdir -p "$(dirname "$KEYS")"
    keytool -genkeypair -keystore "$KEYS" -storepass android -alias androiddebugkey -keypass android \
      -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
  fi
  [ -f "$ES" ] || godot --headless --quit >/dev/null 2>&1 || true
  python3 - "$ES" "$SDK" "$JAVA_HOME_GUESS" "$KEYS" <<'EOF'
import re, sys
p, sdk, java, keys = sys.argv[1:]
s = open(p).read()
want = {"export/android/android_sdk_path": sdk, "export/android/java_sdk_path": java,
        "export/android/debug_keystore": keys, "export/android/debug_keystore_user": "androiddebugkey",
        "export/android/debug_keystore_pass": "android"}
for k, v in want.items():
    line = f'{k} = "{v}"'
    if re.search(rf"^{re.escape(k)} = .*$", s, re.M):
        s = re.sub(rf"^{re.escape(k)} = .*$", line, s, flags=re.M)
    else:
        s = s.replace("[resource]\n", "[resource]\n" + line + "\n", 1)
open(p, "w").write(s)
EOF
}

[ "${1:-}" = "--setup" ] && setup
[ -f "$TPL/android_debug.apk" ] || { echo "Missing export templates: run tools/build_apk.sh --setup"; exit 1; }

mkdir -p "$ROOT/dist"
cd "$ROOT/game"
godot --headless --path . --import >/dev/null 2>&1 || true
godot --headless --path . --export-debug "Android" "$ROOT/dist/purgatory-border-debug.apk" 2>&1 | grep -iE "error|warn" | grep -viE "alsa|audio driver|project icon" || true
test -s "$ROOT/dist/purgatory-border-debug.apk"
"$SDK/build-tools/35.0.1/apksigner" verify "$ROOT/dist/purgatory-border-debug.apk" 2>/dev/null && echo "OK: dist/purgatory-border-debug.apk ($(du -h "$ROOT/dist/purgatory-border-debug.apk" | cut -f1))"
