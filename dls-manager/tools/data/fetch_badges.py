#!/usr/bin/env python3
"""Download club crests from Wikipedia for the local build (assets/ is git-ignored).

For every club in menu/data.json, read the crest file name from the cached Wikipedia
article infobox ("| image = Arsenal FC.svg"), ask the MediaWiki API for a 512px PNG
rendering, download it, and write:
  assets/badges/src/<club id>.png   as downloaded
  assets/badges/256/<club id>.png   256x256 transparent, centred (DLS teams/t<slot>.png)
  assets/badges/64/<club id>.png    64x64 thumbnail (DLS teams/t<slot>_thumb.png)
  assets/badges/128/<club id>.png   128x128 for the menus

Usage: python3 -I fetch_badges.py --data menu/data.json --pages <wp_dir>/pages --out assets/badges
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "menu"))
from export_game_data import WIKI_TITLE, page_file  # noqa: E402

UA = "DLSManagerSquadTool/0.1 (personal non-commercial project; low request rate)"
API = "https://en.wikipedia.org/w/api.php"


def http(url, tries=10):
    delay = 10
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(int(e.headers.get("Retry-After") or delay))
            delay = min(delay * 2, 120)
    raise RuntimeError("too many 429s for " + url)


def crest_file(pages, title):
    path = page_file(pages, title)
    if not os.path.exists(path):
        return None
    txt = open(path).read()
    box = txt[: txt.find("\n}}") + 3] if "{{Infobox" in txt else txt[:6000]
    m = re.search(r"^\|\s*(?:image|logo|crest|badge)\s*=\s*\[?\[?(?:File:|Image:)?([^|\]\n<]+\.(?:svg|png|jpg|jpeg|gif))", box, re.M | re.I)
    return m.group(1).strip() if m else None


def square(img, size):
    img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    w, h = img.size
    scale = (size * 0.94) / max(w, h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = json.load(open(a.data))
    for sub in ("src", "256", "128", "64"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)

    files, missing = {}, []
    for cid, c in data["clubs"].items():
        f = crest_file(a.pages, WIKI_TITLE.get(c["rosterName"], c["rosterName"]))
        if f:
            files[cid] = f
        else:
            missing.append(c["name"])

    todo = [cid for cid in files if not os.path.exists(os.path.join(a.out, "src", cid + ".png"))]
    urls = {}
    for k in range(0, len(todo), 20):
        batch = todo[k:k + 20]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
                                    "iiprop": "url", "iiurlwidth": 512, "titles": "|".join("File:" + files[c] for c in batch)})
        r = json.loads(http(API + "?" + q))
        norm = {n["from"]: n["to"] for n in r["query"].get("normalized", [])}
        info = {p["title"]: p.get("imageinfo", [{}])[0] for p in r["query"]["pages"]}
        for c in batch:
            t = "File:" + files[c]
            ii = info.get(norm.get(t, t), {})
            if ii.get("thumburl") or ii.get("url"):
                urls[c] = ii.get("thumburl") or ii["url"]
            else:
                missing.append(data["clubs"][c]["name"] + f" (file {files[c]!r} not found)")
        time.sleep(3)

    for i, (cid, url) in enumerate(urls.items()):
        raw = http(url)
        open(os.path.join(a.out, "src", cid + ".png"), "wb").write(raw)
        print(f"  {i + 1}/{len(urls)} {cid}", flush=True)
        time.sleep(5)

    done = 0
    for cid in data["clubs"]:
        src = os.path.join(a.out, "src", cid + ".png")
        if not os.path.exists(src):
            continue
        img = Image.open(io.BytesIO(open(src, "rb").read()))
        for size in (256, 128, 64):
            square(img, size).save(os.path.join(a.out, str(size), cid + ".png"), optimize=True)
        done += 1
    print(f"{done}/{len(data['clubs'])} badges ready in {a.out}")
    if missing:
        print("no crest found for:", ", ".join(missing))


if __name__ == "__main__":
    main()
