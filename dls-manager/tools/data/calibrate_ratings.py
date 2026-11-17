#!/usr/bin/env python3
"""Make every player's in-game DLS overall equal their rating in menu/data.json ("ovr").

DLS19 computes the overall shown on player cards (FUN_0018dd14) as
    overall = (sum_k weight[group][k] * attribute_k + 3500) // 1000      (attributes 0-99)
with 13 integer weights per position group (table at libDLS19.so 0x3df268, 13 x i32 per group,
summing to 1000) and the group picked by the player's DLS position code (table at 0x3df530,
23 x i64). Each player's attributes are shifted up or down together (outfield: the ten outfield
ones; goalkeepers: the three goalkeeping ones) until that formula gives their rating.

Writes menu/data.json (attrs), the built players.dat (attr x10) and clubs.json (attr) in place.
Usage: python3 -I calibrate_ratings.py --lib libDLS19.so --data menu/data.json --db <built db dir> --clubs clubs.json
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db"))
import dls_db as D  # noqa: E402

# weight order in the table (by in-memory field) -> database attribute index
# database order: speed, acceleration, stamina, strength, tackling, control, shooting,
# passing, crossing, heading, gk1, gk2, gk3
W_TO_DB = [3, 2, 0, 1, 5, 7, 8, 6, 9, 4, 10, 11, 12]  # STR STA SPE ACC CON PAS CRO SHO HEA TAC G1 G2 G3


def tables(lib):
    d = open(lib, "rb").read()
    grp = struct.unpack_from("<23q", d, 0x3df530)
    w = []
    for g in range(max(grp) + 1):
        row = struct.unpack_from("<13i", d, 0x3df268 + g * 0x34)
        db = [0] * 13
        for k, v in enumerate(row):
            db[W_TO_DB[k]] = v
        w.append(db)
    return grp, w


def overall(a, w):
    return (sum(x * y for x, y in zip(a, w)) + 3500) // 1000


def calibrate(a, w, target, gk):
    a = list(a)
    idx = [10, 11, 12] if gk else list(range(10))
    for _ in range(200):
        o = overall(a, w)
        if o == target:
            break
        step = 1 if target > o else -1
        moved = False
        for i in idx:
            if 1 <= a[i] + step <= 99:
                a[i] += step
                moved = True
        if not moved:
            break
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--clubs", required=True)
    a = ap.parse_args()
    grp, w = tables(a.lib)
    data = json.load(open(a.data, encoding="utf-8"))
    pl = D.Players(D.load(os.path.join(a.db, "players.dat")))
    clubs = json.load(open(a.clubs, encoding="utf-8"))
    by_dls = {}
    for c in clubs.values():
        for x in c["players"]:
            by_dls[x["id"]] = x
    import unicodedata

    def fold(t):
        t = unicodedata.normalize("NFKD", t or "")
        return " ".join("".join(ch for ch in t if not unicodedata.combining(ch)).lower().replace("-", " ").split())
    done = off = 0
    for p in data["players"]:
        c = clubs.get(p["club"])
        hit = next((x["id"] for x in (c["players"] if c else []) if fold(x["fn"] + " " + x["sn"]) == fold(p["name"])), None)
        if hit is None or hit not in pl.by_id:
            continue
        p_dls = hit
        rec = pl.by_id[p_dls]
        g = pl.get(rec)
        pos = g["pos_primary"]
        wt = w[grp[pos]] if pos < len(grp) else w[0]
        new = calibrate(p["attrs"], wt, p["ovr"], pos == 0)
        if overall(new, wt) != p["ovr"]:
            off += 1
        p["attrs"] = new
        pl.set(rec, attr=[x * 10 for x in new])
        if p_dls in by_dls:
            by_dls[p_dls]["attr"] = [x * 10 for x in new]
        done += 1
    D.save_zlib(os.path.join(a.db, "players.dat"), pl.to_bytes())
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(clubs, open(a.clubs, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{done} players calibrated to their rating ({off} could not reach it within 1-99)")


if __name__ == "__main__":
    main()
