#!/usr/bin/env python3
"""Give players their FC positions: the primary one and up to three alternatives.

Reads the owner's ratings sheet export (CSV: two side-by-side tables of Club, Common name,
Position, Alt 1-3, Rating; cells with only "L" / "R" are preferred-foot markers and ignored).
Rows with a name are matched by name within the club. Most rows have none: those match only
when exactly one player of the club has that rating and that primary position in EA's FC
ratings database (the same one ea_attributes.py uses), or, for players not in FC, that
position in our data. Anything ambiguous is left alone (and listed).

Sets "pos" (and "position") to the FC primary position and "alt" to the alternatives, in the
menu's position codes. Usage: python3 -I apply_positions.py --csv sheet.csv --data menu/data.json --ea ea_full.json
"""
import argparse
import csv
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ea_attributes as EA  # noqa: E402

FC = {"GK": "GK", "CB": "CB", "LB": "LB", "LWB": "LB", "RB": "RB", "RWB": "RB", "CDM": "DM", "CM": "CM",
      "CAM": "AM", "LM": "LM", "RM": "RM", "LW": "LW", "RW": "RW", "CF": "SS", "ST": "ST"}
LONG = {"GK": "Goalkeeper", "CB": "Centre-Back", "LB": "Left-Back", "RB": "Right-Back", "DM": "Defensive Midfield",
        "CM": "Central Midfield", "AM": "Attacking Midfield", "LM": "Left Midfield", "RM": "Right Midfield",
        "LW": "Left Winger", "RW": "Right Winger", "SS": "Second Striker", "ST": "Centre-Forward"}
GROUP = {"GK": "GK", "CB": "DF", "LB": "DF", "RB": "DF", "DM": "MF", "CM": "MF", "AM": "MF", "LM": "MF", "RM": "MF",
         "LW": "FW", "RW": "FW", "SS": "FW", "ST": "FW"}
CLUB = {"Atlético de Madrid": "Atlético Madrid", "FC Barcelona": "Barcelona", "AFC Bournemouth": "Bournemouth",
        "RC Celta": "Celta Vigo", "RC Deportivo": "Deportivo", "Elche CF": "Elche", "RCD Espanyol": "Espanyol",
        "Getafe CF": "Getafe", "Ipswich": "Ipswich Town", "Levante UD": "Levante", "Man Utd": "Manchester United",
        "Málaga CF": "Málaga", "Newcastle Utd": "Newcastle United", "Nott'm Forest": "Nottingham Forest",
        "CA Osasuna": "Osasuna", "R. Racing Club": "Racing Santander", "Sevilla FC": "Sevilla",
        "Spurs": "Tottenham Hotspur", "Valencia CF": "Valencia", "Villarreal CF": "Villarreal", "D. Alavés": "Alavés"}


def fix(t):
    try:
        return t.encode("latin1").decode("utf8")
    except Exception:
        return t


def fold(t):
    t = unicodedata.normalize("NFKD", t or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).lower().replace("-", " ").replace(".", " ").split())


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
        for half in (r[0:7], r[8:15]):
            if len(half) == 7 and half[0].strip() and half[6].strip().isdigit():
                h = [fix(x).strip() for x in half]
                pos = [FC[x] for x in h[2:6] if x in FC]
                if pos:
                    rows.append({"club": CLUB.get(h[0], h[0]), "name": h[1], "pos": pos, "ovr": int(h[6])})
    data = json.load(open(a.data, encoding="utf-8"))
    by_club = {}
    for cid, c in data["clubs"].items():
        by_club.setdefault(c["name"], []).append(cid)
    players = {}
    for p in data["players"]:
        players.setdefault(p["club"], []).append(p)
    ea_pos = EA.ea_positions(a.ea, data)          # player id -> FC primary position (our codes)
    used = set()
    done, skipped = 0, []
    for r in sorted(rows, key=lambda r: not r["name"]):
        cids = by_club.get(r["club"])
        if not cids:
            skipped.append((r, "club"))
            continue
        pool = [p for cid in cids for p in players.get(cid, []) if p["id"] not in used]
        hit = None
        if r["name"]:
            nm = fold(r["name"])
            named = [p for p in pool if fold(p["name"]) == nm]
            if not named:
                named = [p for p in pool if nm in (fold(p["name"]).split()[-1], fold(p["name"]).split()[0])]
            if len(named) == 1 and named[0]["ovr"] in (r["ovr"] - 2, r["ovr"] - 1, r["ovr"], r["ovr"] + 1, r["ovr"] + 2):
                hit = named[0]
        if hit is None:   # no name, or a nickname ("Vini Jr."): club, rating and FC position
            same = [p for p in pool if p["ovr"] == r["ovr"] and ea_pos.get(p["id"], p["pos"]) == r["pos"][0]]
            if len(same) == 1:
                hit = same[0]
        if hit is None:
            skipped.append((r, "ambiguous" if r["name"] else "no unique match"))
            continue
        used.add(hit["id"])
        hit["pos"] = r["pos"][0]
        hit["position"] = LONG[r["pos"][0]]
        hit["alt"] = [x for x in dict.fromkeys(r["pos"][1:]) if x != r["pos"][0]]
        done += 1
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{done} players given FC positions, {len(skipped)} rows not matched")
    for r, why in skipped[:60]:
        print("  ", why, r)


if __name__ == "__main__":
    main()
