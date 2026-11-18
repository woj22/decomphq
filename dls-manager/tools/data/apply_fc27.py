#!/usr/bin/env python3
"""Apply the owner's FC27 player sheet: rating, positions and outfield attributes.

CSV (two side-by-side tables): Club, Full name ("Surname, Given"), Common name, Position,
Alt 1-3 ("L"/"R" cells are preferred foot, ignored), Rating, Pace, Acceleration, Stamina,
Short passing, Ball control, Finishing, Crossing, Heading, Standing tackle, Strength.
Goalkeeper rows only have pace; their goalkeeping attributes are kept.

The sheet's Pace column equals Acceleration in every row, so top speed is taken from EA's
sprint speed (ea_full.json) moved by the same amount as acceleration changed, or the
sheet's value for players EA doesn't have.

Players are matched within their club by name (common name, "Given Surname", or all of our
name's words in the full name), with the rating as a check; rows that don't match (women's
teams, other clubs) are listed and skipped. Sets "ovr", "pos"/"position"/"alt" and
"attrs" (DLS order) and "attrSource" = "fc27". Run sync_positions.py and calibrate_ratings.py
afterwards.

Usage: python3 -I apply_fc27.py --csv sheet.csv --data menu/data.json --ea ea_full.json
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_positions as AP  # noqa: E402
import ea_attributes as EA  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--ea", required=True)
    a = ap.parse_args()
    rows = []
    for r in csv.reader(open(a.csv, encoding="utf-8", errors="replace")):
        if r and r[0] == "Club":
            continue
        for h in (r[0:18], r[19:37]):
            if len(h) == 18 and h[0].strip() and h[7].strip().isdigit():
                h = [AP.fix(x).strip() for x in h]
                full = h[1]
                if "," in full:
                    sn, gn = [x.strip() for x in full.split(",", 1)]
                    full = (gn + " " + sn).strip()
                pos = [AP.FC[x] for x in h[3:7] if x in AP.FC]
                num = [int(x) if x.isdigit() else None for x in h[8:18]]
                rows.append({"club": AP.CLUB.get(h[0], h[0]), "full": full, "common": h[2], "pos": pos, "ovr": int(h[7]), "s": num})
    data = json.load(open(a.data, encoding="utf-8"))
    ea = [e for e in json.load(open(a.ea)) if e.get("s")]
    by_dob, by_name = EA.index(ea)
    leagues = {c: v["league"] for c, v in data["clubs"].items()}
    by_club = {}
    for cid, c in data["clubs"].items():
        by_club.setdefault(c["name"], []).append(cid)
    players = {}
    for p in data["players"]:
        players.setdefault(p["club"], []).append(p)
    used, done, skipped = set(), 0, []
    for r in sorted(rows, key=lambda r: -r["ovr"]):
        cids = by_club.get(r["club"])
        if not cids:
            skipped.append(r)
            continue
        pool = [p for cid in cids for p in players.get(cid, []) if p["id"] not in used]
        names = {AP.fold(r["full"]), AP.fold(r["common"])} - {""}
        toks = set(AP.fold(r["full"]).split()) | set(AP.fold(r["common"]).split())
        hit = [p for p in pool if AP.fold(p["name"]) in names]
        if not hit:
            hit = [p for p in pool if set(AP.fold(p["name"]).split()) <= toks]
        if len(hit) > 1:
            hit = [p for p in hit if abs(p["ovr"] - r["ovr"]) <= 3] or hit
        if len(hit) != 1 or abs(hit[0]["ovr"] - r["ovr"]) > 6:
            skipped.append(r)
            continue
        p = hit[0]
        used.add(p["id"])
        p["ovr"] = min(93, r["ovr"])
        if r["pos"]:
            p["pos"] = r["pos"][0]
            p["position"] = AP.LONG[r["pos"][0]]
            p["alt"] = [x for x in dict.fromkeys(r["pos"][1:]) if x != r["pos"][0]]
        s = r["s"]   # pace, acceleration, stamina, short passing, ball control, finishing, crossing, heading, standing tackle, strength
        if p["pos"] != "GK" and all(v is not None for v in s):
            e = EA.find(p, leagues[p["club"]], by_dob, by_name)
            acc = s[1]
            speed = acc
            if e and e["s"].get("sprintSpeed") is not None and e["s"].get("acceleration") is not None:
                speed = max(1, min(99, e["s"]["sprintSpeed"] + (acc - e["s"]["acceleration"])))
            old = p["attrs"]
            p["attrs"] = [speed, acc, s[2], s[9], s[8], s[4], s[5], s[3], s[6], s[7]] + old[10:13]
            p["attrSource"] = "fc27"
        done += 1
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{done} players updated from the sheet, {len(skipped)} rows not matched")
    for r in skipped[:40]:
        print("  ", r["club"], "|", r["full"], "|", r["common"], r["ovr"])


if __name__ == "__main__":
    main()
