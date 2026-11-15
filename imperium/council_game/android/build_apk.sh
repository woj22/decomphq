#!/bin/bash
# Build the Caldera Council APK without Gradle: aapt2 -> javac -> d8 -> zipalign -> apksigner.
# Usage: build_apk.sh <android-sdk> <three.min.js> <out-dir> [version-code] [version-name]
set -euo pipefail
SDK=$1; THREE=$2; OUT=$3; VCODE=${4:-1}; VNAME=${5:-1.0}
HERE=$(cd "$(dirname "$0")" && pwd)
BT=$SDK/build-tools/35.0.0; JAR=$SDK/platforms/android-34/android.jar
W=$OUT/work; rm -rf "$W"; mkdir -p "$W/assets" "$W/classes" "$W/dex"
python3 "$HERE/make_assets.py" "$HERE/../caldera_council.html" "$THREE" "$W/assets" "$W/res"
"$BT/aapt2" compile --dir "$W/res" -o "$W/res.zip"
"$BT/aapt2" link -o "$W/base.apk" -I "$JAR" --manifest "$HERE/AndroidManifest.xml" -R "$W/res.zip" -A "$W/assets" \
  --min-sdk-version 24 --target-sdk-version 34 --version-code "$VCODE" --version-name "$VNAME"
javac -nowarn -source 8 -target 8 -bootclasspath "$JAR" -d "$W/classes" $(find "$HERE/src" -name '*.java') 2>&1 | grep -v "^warning\|^Note\|^1 warning" || true
"$BT/d8" --lib "$JAR" --min-api 24 --output "$W/dex" $(find "$W/classes" -name '*.class')
(cd "$W/dex" && zip -q -j "$W/base.apk" classes.dex)
"$BT/zipalign" -p -f 4 "$W/base.apk" "$W/aligned.apk"
KS=${KEYSTORE:-$HERE/caldera.keystore}
[ -f "$KS" ] || keytool -genkeypair -keystore "$KS" -storepass android -keypass android -alias caldera -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Caldera Council" >/dev/null 2>&1
APK="$OUT/Caldera_Council_v$VNAME.apk"
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android --out "$APK" "$W/aligned.apk"
"$BT/apksigner" verify "$APK" && echo "built $APK"
