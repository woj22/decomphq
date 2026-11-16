#!/usr/bin/env bash
# Build Elosia_AlienCity.mcworld from the original Elosia download (used locally and by GitHub Actions).
#   bash minecraft_alien/elosia/make_world.sh [WORKDIR]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
D="${1:-/home/user/elosia}"
export ELOSIA_DIR="$D"
PY="${PYTHON:-python3}"
mkdir -p "$D" && cd "$D"
if [ ! -s Elosia_Bedrock.zip ]; then
  curl -sSL -A "Mozilla/5.0" -o page.html "https://www.mediafire.com/file_premium/mbiwqw6jcl4c3in/Elosia_Bedrock.zip/file"
  URL=$(grep -oE 'https://download[0-9]*\.mediafire\.com[^"'"'"' ]+' page.html | head -1)
  [ -n "$URL" ] || { echo "could not find the Mediafire download link"; exit 1; }
  curl -sSL -A "Mozilla/5.0" -o Elosia_Bedrock.zip "$URL"
fi
rm -rf src work && mkdir -p work
unzip -q Elosia_Bedrock.zip -d src
cp -r "src/Map & Info/Elosia" work/Elosia
"$PY" "$HERE/heightmap.py"
"$PY" "$HERE/place_city.py" work/Elosia
"$PY" "$HERE/finalize_world.py" work/Elosia "Elosia - Alien City"
"$PY" "$HERE/render_area.py" work/Elosia city_map.png
rm -f Elosia_AlienCity.mcworld
(cd work/Elosia && zip -qr -1 ../../Elosia_AlienCity.mcworld db level.dat levelname.txt world_icon.jpeg)
ls -la Elosia_AlienCity.mcworld city_map.png
