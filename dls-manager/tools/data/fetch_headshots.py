#!/usr/bin/env python3
"""Player headshots for the menus, from each player's Wikipedia article image (Commons).

1. Menu players (menu/data.json) are matched to the article titles in the cached Wikipedia
   squad lists (by club, then shirt number or name).
2. MediaWiki pageimages gives each article's lead image (20 titles per request).
3. The image is downloaded small, the face found with OpenCV's frontal-face detector and a
   square crop around it saved as <out>/<player id>.jpg (96 px). Without a face the photo
   is skipped rather than guessed.

Polite to Wikimedia: descriptive User-Agent, one request at a time, short pauses; files
already present are not fetched again.

Usage: python3 -I fetch_headshots.py --data menu/data.json --squads <squads.json> --out assets/headshots
"""
import argparse
import json
import os
import subprocess
import time
import unicodedata
import urllib.parse

import cv2
import numpy as np

UA = "DLSManagerSquadTool/0.1 (personal non-commercial project; low request rate)"
API = "https://en.wikipedia.org/w/api.php"
SIZE = 96


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace("-", " ").strip()


def curl(url, out=None):
    cmd = ["curl", "-sSL", "--max-time", "40", "-A", UA, url]
    if out:
        cmd += ["-o", out]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[:200])
    return r.stdout


def page_images(titles):
    q = {"action": "query", "format": "json", "prop": "pageimages", "piprop": "thumbnail",
         "pithumbsize": "400", "redirects": "1", "titles": "|".join(titles)}
    for attempt in range(4):
        raw = curl(API + "?" + urllib.parse.urlencode(q))
        try:
            data = json.loads(raw)
            break
        except ValueError:  # rate limited (HTML/empty reply): back off and retry
            time.sleep(5 * (attempt + 1))
    else:
        return {t: None for t in titles}
    norm = {n["from"]: n["to"] for n in data.get("query", {}).get("normalized", [])}
    redir = {n["from"]: n["to"] for n in data.get("query", {}).get("redirects", [])}
    by_title = {p["title"]: p.get("thumbnail", {}).get("source") for p in data.get("query", {}).get("pages", {}).values()}
    out = {}
    for t in titles:
        x = norm.get(t, t)
        x = redir.get(x, x)
        out[t] = by_title.get(x)
    return out


FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def face_crop(path, out):
    img = cv2.imread(path)
    if img is None:
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = FACE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return False
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # biggest face = the subject
    cx, cy = x + w / 2, y + h / 2 + h * 0.08
    side = int(w * 1.9)  # head and a bit of shoulders
    x0 = int(max(0, min(img.shape[1] - side, cx - side / 2)))
    y0 = int(max(0, min(img.shape[0] - side, cy - side / 2)))
    side = min(side, img.shape[0], img.shape[1])
    crop = img[y0:y0 + side, x0:x0 + side]
    crop = cv2.resize(crop, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    cv2.imwrite(out, crop, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--squads", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(a.out, "_src")
    os.makedirs(tmp, exist_ok=True)
    data = json.load(open(a.data, encoding="utf-8"))
    squads = json.load(open(a.squads, encoding="utf-8"))
    wiki = {club: rows for lg in squads.values() for club, rows in lg.items()}

    # ---- match players to article titles
    want = {}  # player id -> article title
    for p in data["players"]:
        c = data["clubs"][p["club"]]
        rows = wiki.get(c["rosterName"])
        if not rows:
            continue
        hit = None
        for r in rows:
            if r.get("article") and fold(r["name"]) == fold(p["name"]):
                hit = r
                break
        if not hit and p.get("shirt") is not None:
            for r in rows:
                if r.get("article") and r.get("no") == str(p["shirt"]):
                    sn = fold(p["name"]).split()[-1]
                    if sn and sn in fold(r["name"]):
                        hit = r
                        break
        if hit:
            want[p["id"]] = hit["article"]
    print(f"{len(want)} of {len(data['players'])} players matched to an article")

    # ---- image urls, 50 titles per request
    todo = [pid for pid in want if not os.path.exists(os.path.join(a.out, f"{pid}.jpg"))]
    titles = sorted({want[pid] for pid in todo})
    urls = {}
    for i in range(0, len(titles), 20):
        urls.update(page_images(titles[i:i + 20]))
        time.sleep(1.5)
    print(f"{sum(1 for u in urls.values() if u)} of {len(titles)} articles have a lead image")

    ok = noface = noimg = 0
    for pid in todo:
        u = urls.get(want[pid])
        if not u:
            noimg += 1
            continue
        src = os.path.join(tmp, f"{pid}{os.path.splitext(urllib.parse.urlparse(u).path)[1] or '.jpg'}")
        if not os.path.exists(src):
            try:
                curl(u, src)
            except Exception as e:
                print("download failed", pid, e)
                continue
            time.sleep(0.3)
        if face_crop(src, os.path.join(a.out, f"{pid}.jpg")):
            ok += 1
        else:
            noface += 1
    have = len([f for f in os.listdir(a.out) if f.endswith(".jpg")])
    print(f"new headshots {ok}, no image {noimg}, no face found {noface}; total {have}")


if __name__ == "__main__":
    main()
