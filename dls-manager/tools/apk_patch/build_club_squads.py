#!/usr/bin/env python3
"""Export every manager club's DLS squad for the on-device Dream FC conversion.

Writes clubs.json for assets/dlsmgr/: {club id: {tid, name, short, stadium, players: [...]}}
with exactly the fields Overlay.becomeClub writes into the profile's custom player records
(names, nationality, height, positions, foot, 13 ratings 0-1000, birth date, shirt, link flags).

Usage: python3 -I build_club_squads.py --db <built db dir> --data menu/data.json --out clubs.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "db"))
import dls_db as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = json.load(open(a.data, encoding="utf-8"))
    slots = json.load(open(os.path.join(a.db, "slots.json"), encoding="utf-8"))
    pl = D.Players(D.load(os.path.join(a.db, "players.dat")))
    ln = D.Links(D.load(os.path.join(a.db, "teamplayerlinks_0.dat")))
    out = {}
    for cid, c in data["clubs"].items():
        tid = slots[cid]
        players = []
        for e in ln.teams[tid][:32]:
            g = pl.get(pl.by_id[e["player_id"]])
            players.append({
                "id": e["player_id"], "fn": g["first_name"], "sn": g["surname"], "nat": g["nationality"],
                "h": g["height_cm"], "pos": g["pos_primary"], "pos2": g["pos_secondary"],
                "foot": g["foot"], "attr": g["attr"],
                "by": g["birth_year"], "bm": g["birth_month"], "bd": g["birth_day"],
                "shirt": e["shirt"], "flags": e["flags"], "slot": e["slot"],
            })
        out[cid] = {"tid": tid, "name": c["name"], "short": c["short"], "stadium": c["stadium"], "players": players}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(out), "clubs,", sum(len(v["players"]) for v in out.values()), "players ->", a.out)


if __name__ == "__main__":
    main()
