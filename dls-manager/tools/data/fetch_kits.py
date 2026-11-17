#!/usr/bin/env python3
"""Real 2026/27 kit colours from the Wikipedia club infoboxes.

Wikipedia draws a kit as a base colour (body1, leftarm1, shorts1, socks1; 2 = away,
3 = third) with an optional pattern image on top (pattern_b1 = "_arsenal2627h" ->
File:Kit_body_arsenal2627h.png). Base colours alone are wrong for striped or fully
drawn kits, so this script downloads the pattern images, composites them over the
base colour exactly as the template does, and measures what is visible:

  data/kits_2026_27.json
  {club id: {"home"|"away"|"third": {"shirt": "#RRGGBB", "shirt2": "#RRGGBB",
             "sleeves": "#RRGGBB", "shorts": "#RRGGBB", "socks": "#RRGGBB",
             "pattern": "plain"|"stripes"|"hoops"|"other"}}}

Pattern images go to assets/kits/src (git-ignored). Resumable; slow on purpose.
Usage: python3 -I fetch_kits.py --data menu/data.json --pages <wp_dir>/pages --out data/kits_2026_27.json
"""
import argparse
import collections
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "menu"))
from export_game_data import WIKI_TITLE, page_file  # noqa: E402

UA = "DLSManagerSquadTool/0.1 (personal non-commercial project; low request rate)"
PARTS = {"body": ("body", "pattern_b", "Kit_body"), "sleeves": ("leftarm", "pattern_la", "Kit_left_arm"),
         "shorts": ("shorts", "pattern_sh", "Kit_shorts"), "socks": ("socks", "pattern_so", "Kit_socks")}
KITS = {"1": "home", "2": "away", "3": "third"}


def curl(url, out=None):
    """curl is used because Python's urllib stalls on this proxy for upload.wikimedia.org."""
    args = ["curl", "-s", "-m", "60", "-A", UA, url]
    if out:
        args += ["-o", out, "-w", "%{http_code}"]
    r = subprocess.run(args, capture_output=True)
    return r.stdout


def field(txt, name):
    m = re.search(r"^\|\s*%s\s*=\s*#?([^|\n<]*)" % re.escape(name), txt, re.M)
    return m.group(1).strip() if m else ""


def hexcol(v, default="FFFFFF"):
    return v.upper() if re.fullmatch(r"[0-9A-Fa-f]{6}", v or "") else default


def image_urls(files, cache):
    todo = [f for f in files if f not in cache]
    for k in range(0, len(todo), 40):
        batch = todo[k:k + 40]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
                                    "iiprop": "url", "titles": "|".join("File:" + f for f in batch)})
        for attempt in range(6):
            raw = curl("https://en.wikipedia.org/w/api.php?" + q)
            try:
                r = json.loads(raw)
                break
            except ValueError:
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit("Wikipedia API kept refusing; try again later")
        norm = {n["from"]: n["to"] for n in r["query"].get("normalized", [])}
        info = {p["title"]: p for p in r["query"]["pages"]}
        for f in batch:
            p = info.get(norm.get("File:" + f, "File:" + f), {})
            cache[f] = (p.get("imageinfo") or [{}])[0].get("url")
        time.sleep(5)
    return cache


def measure(img, base):
    """Composite the pattern over the base colour and return colours by visible area."""
    w, h = img.size
    bg = Image.new("RGBA", (w, h), tuple(int(base[i:i + 2], 16) for i in (0, 2, 4)) + (255,))
    comp = Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
    counts = collections.Counter()
    for (r, g, b) in comp.getdata():
        counts[(r // 24 * 24, g // 24 * 24, b // 24 * 24)] += 1
    total = sum(counts.values())
    cols = []
    for (r, g, b), n in counts.most_common(6):  # merge near-duplicates
        if all(abs(r - x) + abs(g - y) + abs(b - z) > 60 for (x, y, z), _ in cols):
            cols.append(((r, g, b), n / total))
    # vertical vs horizontal alternation tells stripes from hoops
    rows = [comp.getpixel((x, h // 2)) for x in range(w)]
    colsv = [comp.getpixel((w // 2, y)) for y in range(h)]
    flips = lambda seq: sum(1 for a, b in zip(seq, seq[1:]) if sum(abs(p - q) for p, q in zip(a, b)) > 120)
    return cols, flips(rows), flips(colsv)


def tohex(c):
    return "#%02X%02X%02X" % c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = json.load(open(a.data))
    src_dir = os.path.join(HERE, "..", "..", "assets", "kits", "src")
    os.makedirs(src_dir, exist_ok=True)
    cache_path = os.path.join(src_dir, "_urls.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}

    plan = {}
    for cid, c in data["clubs"].items():
        p = page_file(a.pages, WIKI_TITLE.get(c["rosterName"], c["rosterName"]))
        txt = open(p).read() if os.path.exists(p) else ""
        plan[cid] = {}
        for k, kit in KITS.items():
            parts = {}
            for part, (col, pat, prefix) in PARTS.items():
                base, pattern = field(txt, col + k), field(txt, pat + k)
                if not base and not pattern:
                    continue
                parts[part] = {"base": hexcol(base), "file": f"{prefix}{pattern}.png" if pattern else None}
            if parts:
                plan[cid][kit] = parts

    files = sorted({pt["file"] for kits in plan.values() for parts in kits.values() for pt in parts.values() if pt["file"]})
    image_urls(files, cache)
    json.dump(cache, open(cache_path, "w"), indent=0)
    for f in files:
        dst = os.path.join(src_dir, f)
        if cache.get(f) and not os.path.exists(dst):
            curl(cache[f], dst)
            time.sleep(1)

    out = {}
    for cid, kits in plan.items():
        out[cid] = {}
        for kit, parts in kits.items():
            res = {}
            for part, pt in parts.items():
                path = os.path.join(src_dir, pt["file"]) if pt["file"] else None
                if path and os.path.exists(path) and os.path.getsize(path) > 0:
                    cols, fh, fv = measure(Image.open(path), pt["base"])
                else:
                    cols, fh, fv = [(tuple(int(pt["base"][i:i + 2], 16) for i in (0, 2, 4)), 1.0)], 0, 0
                res[part] = {"cols": [(tohex(c), round(s, 2)) for c, s in cols], "fh": fh, "fv": fv}
            body = res.get("body") or next(iter(res.values()))
            main = body["cols"][0][0]
            second = body["cols"][1][0] if len(body["cols"]) > 1 and body["cols"][1][1] >= 0.12 else None
            pattern = "plain"
            if second:
                pattern = "stripes" if body["fh"] >= 4 and body["fh"] > body["fv"] else "hoops" if body["fv"] >= 4 else "other"
            sleeves = res.get("sleeves", body)["cols"][0][0]
            out[cid][kit] = {
                "shirt": main, "shirt2": second or sleeves, "sleeves": sleeves,
                "shorts": res.get("shorts", {"cols": [(main, 1)]})["cols"][0][0],
                "socks": res.get("socks", {"cols": [(main, 1)]})["cols"][0][0], "pattern": pattern,
            }
    json.dump(out, open(a.out, "w"), indent=1)
    have = sum(1 for v in out.values() if "home" in v)
    print(f"{have}/{len(out)} clubs with a home kit; pattern images: {len(files)}")
    print("no kit data:", [data["clubs"][c]["name"] for c, v in out.items() if "home" not in v])


if __name__ == "__main__":
    main()
