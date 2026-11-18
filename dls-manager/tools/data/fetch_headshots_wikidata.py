#!/usr/bin/env python3
"""More player headshots: Wikidata's image (P18, a Wikimedia Commons photo) for players the
Wikipedia squad lists didn't give one.

For each menu player without <out>/<id>.jpg: search Wikidata by name, keep the candidate
with the same date of birth (P569), take its image (P18), download a 400px thumbnail from
Commons and crop the face (same OpenCV crop as fetch_headshots.py). Players whose birth date
doesn't match any candidate are skipped rather than guessed.

Polite: descriptive User-Agent, one request at a time, short pauses; files already present
are not fetched again. Commons photos are freely licensed (attribution on Commons).

Usage: python3 -I fetch_headshots_wikidata.py --data menu/data.json --out assets/headshots
"""
import argparse
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_headshots as H  # noqa: E402

WD = "https://www.wikidata.org/w/api.php"


def api(q):
    for attempt in range(4):
        try:
            return json.loads(H.curl(WD + "?" + urllib.parse.urlencode(q)))
        except Exception:
            time.sleep(4 * (attempt + 1))
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(a.out, "_src")
    os.makedirs(tmp, exist_ok=True)
    data = json.load(open(a.data, encoding="utf-8"))
    todo = [p for p in data["players"] if p.get("dob") and not os.path.exists(os.path.join(a.out, f"{p['id']}.jpg"))]
    if a.limit:
        todo = todo[: a.limit]
    print(len(todo), "players to look up", flush=True)
    ok = nomatch = noimg = noface = 0
    for n, p in enumerate(todo):
        res = api({"action": "wbsearchentities", "search": p["name"], "language": "en", "type": "item", "limit": "7", "format": "json"})
        ids = [x["id"] for x in res.get("search", [])]
        time.sleep(0.25)
        if not ids:
            nomatch += 1
            continue
        ents = api({"action": "wbgetentities", "ids": "|".join(ids), "props": "claims", "format": "json"}).get("entities", {})
        time.sleep(0.25)
        img = None
        found = False
        for eid in ids:
            cl = ents.get(eid, {}).get("claims", {})
            dobs = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("time", "") for c in cl.get("P569", [])]
            if any(d[1:11] == p["dob"] for d in dobs):
                found = True
                imgs = [c["mainsnak"].get("datavalue", {}).get("value") for c in cl.get("P18", [])]
                img = next((x for x in imgs if x), None)
                break
        if not found:
            nomatch += 1
            continue
        if not img:
            noimg += 1
            continue
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(img.replace(" ", "_")) + "?width=400"
        src = os.path.join(tmp, f"{p['id']}_wd.jpg")
        try:
            H.curl(url, src)
        except Exception as e:
            print("download failed", p["name"], e, flush=True)
            continue
        time.sleep(0.3)
        if H.face_crop(src, os.path.join(a.out, f"{p['id']}.jpg")):
            ok += 1
        else:
            noface += 1
        if n % 100 == 0:
            print(n, "done:", ok, "new", flush=True)
    print(f"new headshots {ok}; no Wikidata match {nomatch}; no image {noimg}; no face found {noface}", flush=True)


if __name__ == "__main__":
    main()
