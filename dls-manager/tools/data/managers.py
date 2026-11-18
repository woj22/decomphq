#!/usr/bin/env python3
"""Each club's manager / head coach (menu/data.json clubs[*].manager), from the "manager"
field of the club's Wikipedia infobox (cached pages, as used for kit colours).

Usage: python3 -I managers.py --data menu/data.json --pages <dir of cached .wiki pages>
"""
import argparse
import glob
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "menu"))


def fold(t):
    t = unicodedata.normalize("NFKD", t or "")
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if not unicodedata.combining(c)).lower())


def manager_of(txt):
    m = re.search(r"^\s*\|\s*manager\s*=\s*(.+)$", txt, re.M)
    if not m:
        return None
    v = m.group(1)
    if v.strip().startswith("|"):
        return None
    v = re.sub(r"<ref.*?(</ref>|/>)", "", v)
    v = re.sub(r"\{\{[^}]*\}\}", "", v)
    v = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", v)
    v = re.sub(r"<[^>]+>", "", v).strip(" '\"")
    v = re.split(r"\s*\(|<br|,", v)[0].strip()
    return v or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pages", required=True)
    a = ap.parse_args()
    data = json.load(open(a.data, encoding="utf-8"))
    pages = {fold(os.path.basename(f)[:-5].replace("_", " ")): f for f in glob.glob(os.path.join(a.pages, "*.wiki"))}
    import export_game_data as X
    titles = {v: k for k, v in X.WIKI_TITLE.items()}
    n = 0
    for cid, c in data["clubs"].items():
        cands = [c.get("rosterName"), X.WIKI_TITLE.get(c.get("rosterName")), c["name"], c["name"] + " F.C.", c["name"] + " FC", c["name"] + " CF", "NK " + c["name"], "ND " + c["name"]]
        f = next((pages[fold(t)] for t in cands if t and fold(t) in pages), None)
        mgr = manager_of(open(f, encoding="utf-8").read()) if f else None
        if mgr:
            c["manager"] = mgr
            n += 1
        else:
            print("no manager:", cid, c.get("rosterName"))
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(n, "managers")


if __name__ == "__main__":
    main()
