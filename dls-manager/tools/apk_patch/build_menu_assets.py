#!/usr/bin/env python3
"""Package the manager menus for the APK (assets/dlsmgr/).

The page is the same menu/index.html as the web preview, with three changes for running
from file:///android_asset inside the game:
  * data.json becomes data.js (window.DLS_DATA = ...), because file:// pages cannot fetch;
  * the Google Fonts link is replaced by bundled Manrope @font-face rules (works offline);
  * badges are copied next to it (badges/<club>.png, 128 px).

Usage: python3 -I build_menu_assets.py --menu menu --badges assets/badges/128 --fonts <dir with Manrope-*.ttf> --out <dir>
Then add every file under <out> to the APK as assets/dlsmgr/<path>.
"""
import argparse
import json
import os
import re
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--menu", required=True)
    ap.add_argument("--badges", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--leagues", help="folder of league logos <league id>.png (copied to leagues/)")
    ap.add_argument("--clubs", help="clubs.json (build_club_squads.py): adds each player's DLS id as 'dls'")
    ap.add_argument("--ui", help="folder of title / loading pictures and logos (copied to bg/)")
    ap.add_argument("--photos", help="folder of player headshots <player id>.jpg (Wikimedia Commons; resized to photos/, listed in photos/list.js)")
    ap.add_argument("--music", help="folder of menu songs (.m4a/.mp3/.ogg, copied to music/ and listed in music/list.js)")
    a = ap.parse_args()

    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(os.path.join(a.out, "badges"))
    os.makedirs(os.path.join(a.out, "fonts"))

    html = open(os.path.join(a.menu, "index.html"), encoding="utf-8").read()
    faces = []
    for f in sorted(os.listdir(a.fonts)):
        m = re.match(r"Manrope-(\d+)\.ttf$", f)
        if m:
            shutil.copy(os.path.join(a.fonts, f), os.path.join(a.out, "fonts", f))
            faces.append("@font-face{font-family:Manrope;font-weight:%s;font-style:normal;"
                         "src:url(fonts/%s) format('truetype');}" % (m.group(1), f))
    html = re.sub(r'<link rel="preconnect"[^>]*>\s*', "", html)
    html = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>',
                  "<style>" + "".join(faces) + "</style>", html)
    if "<!doctype" not in html.lower():  # the preview relies on the host's skeleton; give the app a full page
        html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                'content="width=device-width,initial-scale=1,viewport-fit=cover">'
                # installable from a phone's browser (Add to Home Screen): name, icon, full screen
                '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
                '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
                '<meta name="apple-mobile-web-app-title" content="Assistant Manager"><meta name="theme-color" content="#0b0e0d">'
                '<link rel="apple-touch-icon" href="bg/icon-180.png"><link rel="manifest" href="manifest.json"></head><body>\n'
                + html + "\n</body></html>\n")
    json.dump({"name": "Assistant Manager 27", "short_name": "Assistant Manager", "start_url": "./", "scope": "./", "display": "fullscreen",
               "orientation": "landscape", "background_color": "#0b0e0d", "theme_color": "#0b0e0d",
               "icons": [{"src": "bg/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "bg/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
              open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    html = html.replace("<script>", '<script src="data.js"></script>\n<script src="music/list.js"></script>\n<script src="photos/list.js"></script>\n<script>', 1)
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(html)

    data = json.load(open(os.path.join(a.menu, "data.json"), encoding="utf-8"))
    if a.clubs:
        # the menus' player ids are their own; the match needs DLS database ids (same club, same name)
        import unicodedata

        def fold(s):
            s = unicodedata.normalize("NFKD", s or "")
            return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().replace("-", " ").split())
        clubs = json.load(open(a.clubs, encoding="utf-8"))
        hit = 0
        for p in data["players"]:
            c = clubs.get(p["club"])
            if not c:
                continue
            for x in c["players"]:
                if fold(x["fn"] + " " + x["sn"]) == fold(p["name"]):
                    p["dls"] = x["id"]
                    hit += 1
                    break
        print(f"DLS ids for {hit} of {len(data['players'])} players")
    open(os.path.join(a.out, "data.js"), "w", encoding="utf-8").write(
        "window.DLS_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")

    if a.leagues and os.path.isdir(a.leagues):
        os.makedirs(os.path.join(a.out, "leagues"), exist_ok=True)
        for f in os.listdir(a.leagues):
            if f.endswith(".png"):
                shutil.copy(os.path.join(a.leagues, f), os.path.join(a.out, "leagues", f))
    n = 0
    for f in os.listdir(a.badges):
        if f.endswith(".png"):
            shutil.copy(os.path.join(a.badges, f), os.path.join(a.out, "badges", f))
            n += 1
    if a.ui:
        os.makedirs(os.path.join(a.out, "bg"), exist_ok=True)
        for f in os.listdir(a.ui):
            if f.lower().endswith((".jpg", ".png")):
                shutil.copy(os.path.join(a.ui, f), os.path.join(a.out, "bg", f))
    photos = []
    if a.photos:
        from PIL import Image
        os.makedirs(os.path.join(a.out, "photos"), exist_ok=True)
        for f in sorted(os.listdir(a.photos)):
            m = re.match(r"(\d+)\.jpe?g$", f)
            if not m:
                continue
            try:
                im = Image.open(os.path.join(a.photos, f)).convert("RGB")
            except Exception:
                continue
            w, h = im.size
            side = min(w, h)
            im = im.crop(((w - side) // 2, 0, (w - side) // 2 + side, side)).resize((160, 160), Image.LANCZOS)
            im.save(os.path.join(a.out, "photos", m.group(1) + ".jpg"), quality=78, optimize=True, progressive=True)
            photos.append(int(m.group(1)))
        with open(os.path.join(a.out, "photos", "list.js"), "w") as fh:
            fh.write("window.PHOTO_IDS = " + json.dumps(photos) + ";\n")
    songs = []
    if a.music:
        os.makedirs(os.path.join(a.out, "music"), exist_ok=True)
        for f in sorted(os.listdir(a.music)):
            if f.lower().endswith((".m4a", ".mp3", ".ogg")):
                shutil.copy(os.path.join(a.music, f), os.path.join(a.out, "music", f))
                songs.append("music/" + f)
        titles = {}
        tp = os.path.join(a.music, "titles.json")   # {"01.m4a": {"t": title, "a": artist}}
        if os.path.exists(tp):
            titles = {"music/" + k: v for k, v in json.load(open(tp, encoding="utf-8")).items()}
        with open(os.path.join(a.out, "music", "list.js"), "w", encoding="utf-8") as fh:
            fh.write("window.MUSIC_FILES = " + json.dumps(songs) + ";\nwindow.MUSIC_TITLES = " + json.dumps(titles, ensure_ascii=False) + ";\n")
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(a.out) for f in fs)
    print(f"menu assets: index.html, data.js, {n} badges, {len(faces)} font weights, {len(songs)} songs, {len(photos)} photos, {size // 1024} KB -> {a.out}")


if __name__ == "__main__":
    main()
