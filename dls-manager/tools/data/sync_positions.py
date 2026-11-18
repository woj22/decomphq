#!/usr/bin/env python3
"""Write menu/data.json's positions into the built DLS database and clubs.json.

pos_primary = the player's position, pos_secondary = their first alternative (or the same),
as DLS position codes. Run calibrate_ratings.py afterwards: the overall formula's weights
depend on the position.

Usage: python3 -I sync_positions.py --data menu/data.json --db <built db dir> --clubs clubs.json
"""
import argparse
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db"))
import dls_db as D  # noqa: E402

CODE = {"GK": 0, "LB": 1, "RB": 2, "CB": 5, "DM": 8, "CM": 9, "RM": 16, "RW": 16, "LM": 17, "LW": 17, "AM": 18, "SS": 19, "ST": 19}


def fold(t):
    t = unicodedata.normalize("NFKD", t or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).lower().replace("-", " ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--clubs", required=True)
    a = ap.parse_args()
    data = json.load(open(a.data, encoding="utf-8"))
    clubs = json.load(open(a.clubs, encoding="utf-8"))
    pl = D.Players(D.load(os.path.join(a.db, "players.dat")))
    n = 0
    for p in data["players"]:
        c = clubs.get(p["club"])
        x = next((x for x in (c["players"] if c else []) if fold(x["fn"] + " " + x["sn"]) == fold(p["name"])), None)
        if x is None or x["id"] not in pl.by_id:
            continue
        p1 = CODE[p["pos"]]
        p2 = CODE[p["alt"][0]] if p.get("alt") else p1
        if (x["pos"], x["pos2"]) != (p1, p2):
            x["pos"], x["pos2"] = p1, p2
            pl.set(pl.by_id[x["id"]], pos_primary=p1, pos_secondary=p2)
            n += 1
    D.save_zlib(os.path.join(a.db, "players.dat"), pl.to_bytes())
    json.dump(clubs, open(a.clubs, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{n} players' DLS positions updated")


if __name__ == "__main__":
    main()
