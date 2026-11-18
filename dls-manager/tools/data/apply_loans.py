#!/usr/bin/env python3
"""Mark the players who are on loan at the start of the season (menu/data.json).

The roster's "signed_from" says "<club> (loan)" for loanees. A loan from one of our clubs
sets "loanFrom" (club id): the player belongs to that club and returns there when the season
ends. A loan from a club outside the game sets "loanFromName"; he goes back abroad.

Usage: python3 -I apply_loans.py --roster data/roster_2026_27.json --data menu/data.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_positions as AP  # noqa: E402

ALIAS = {"ipswich": "ipswich-town", "atletico": "atletico-madrid", "atlético": "atletico-madrid", "barcelona": "barcelona",
         "celta": "celta-vigo", "athletic": "athletic-club", "valencia": "valencia", "sevilla": "sevilla", "villarreal": "villarreal",
         "chelsea": "chelsea", "newcastle": "newcastle-united", "liverpool": "liverpool", "manchester united": "manchester-united"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", required=True)
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    loans = []

    def walk(o):
        if isinstance(o, dict):
            sf = str(o.get("signed_from") or "")
            if "(loan)" in sf.lower() and o.get("name"):
                loans.append((o["name"], sf[: sf.lower().index("(loan)")].strip()))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.load(open(a.roster, encoding="utf-8")))
    data = json.load(open(a.data, encoding="utf-8"))
    by = {}
    for p in data["players"]:
        by.setdefault(AP.fold(p["name"]), []).append(p)
    n = 0
    for name, parent in loans:
        ps = by.get(AP.fold(name), [])
        if len(ps) != 1:
            print("not found:", name)
            continue
        p = ps[0]
        cid = ALIAS.get(AP.fold(parent))
        if cid and cid in data["clubs"] and cid != p["club"]:
            p["loanFrom"] = cid
        else:
            p["loanFromName"] = parent
        n += 1
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(n, "loans marked")


if __name__ == "__main__":
    main()
