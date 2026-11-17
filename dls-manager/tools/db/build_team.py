#!/usr/bin/env python3
"""Write one club from data/roster_2026_27.json into a DLS19 team slot.

The club's players overwrite the player records currently linked to that slot (and, if
the new squad is bigger, other records nobody else uses), so file sizes stay the same.
Ratings are estimated from market value, age and position until real ratings exist.

Usage:
  python3 -I build_team.py --db <dir with original players.dat, teamplayerlinks_0.dat,
         teams.dat, ftsteamnames.xlc> --roster data/roster_2026_27.json
         --club "Arsenal F.C." --team-id 0 --out <dir>
         [--long-name "Arsenal"] [--short-name ARS] [--stadium "Emirates Stadium"]
"""
import argparse
import datetime
import hashlib
import json
import math
import unicodedata
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dls_db as D  # noqa: E402

TODAY = datetime.date(2026, 11, 17)

# Position -> (group, natural slot code used in teamplayerlinks / pos_primary)
POS = {
    "Goalkeeper": ("GK", 0), "Left-Back": ("FB", 1), "Right-Back": ("FB", 2), "Centre-Back": ("CB", 5),
    "Defensive Midfield": ("DM", 8), "Central Midfield": ("CM", 9), "Left Midfield": ("W", 17),
    "Right Midfield": ("W", 16), "Attacking Midfield": ("AM", 18), "Left Winger": ("W", 17),
    "Right Winger": ("W", 16), "Second Striker": ("ST", 19), "Centre-Forward": ("ST", 19),
    "Defender": ("CB", 5), "Midfield": ("CM", 9), "Attack": ("ST", 19),
}
# Offsets from the overall rating for: speed, accel, stamina, strength, tackling,
# control, shooting, passing_a, passing_b, heading
SHAPE = {
    "GK": [-25, -25, -20, -10, -30, -25, -40, -20, -15, -25],
    "CB": [-8, -10, 0, 6, 8, -10, -25, -8, -5, 6],
    "FB": [4, 4, 4, -4, 2, -3, -20, -4, -2, -8],
    "DM": [-7, -7, 5, 3, 6, -1, -12, 1, 3, -4],
    "CM": [-4, -4, 4, -4, -5, 2, -6, 3, 5, -10],
    "AM": [0, 2, -2, -10, -20, 5, 0, 2, 4, -15],
    "W": [6, 7, 0, -10, -22, 4, -3, -6, -2, -18],
    "ST": [1, 2, -3, 2, -25, 0, 5, -12, -6, 4],
}
# Original Arsenal starting-XI slot layout (4-2-3-1): GK, LB, RB, CB, CB, CM, CM, RM, LM, AM, ST
XI_SLOTS = [("GK", 0), ("LB", 1), ("RB", 2), ("CB", 5), ("CB", 7), ("CM", 9), ("CM", 10),
            ("RW", 16), ("LW", 17), ("AM", 18), ("ST", 19)]
SLOT_FITS = {
    "GK": {"Goalkeeper"}, "LB": {"Left-Back"}, "RB": {"Right-Back"}, "CB": {"Centre-Back", "Defender"},
    "CM": {"Central Midfield", "Defensive Midfield", "Midfield"},
    "RW": {"Right Winger", "Right Midfield"}, "LW": {"Left Winger", "Left Midfield"},
    "AM": {"Attacking Midfield", "Second Striker"}, "ST": {"Centre-Forward", "Attack", "Second Striker"},
}


def jitter(name, k, span=3):
    h = hashlib.sha1(f"{name}:{k}".encode()).digest()[0]
    return (h % (2 * span + 1)) - span


def age_of(p):
    if p.get("dob"):
        d = datetime.date.fromisoformat(p["dob"])
        return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))
    return p.get("age") or 26


def overall(p):
    """Rough 0-100 rating from market value (placeholder until real ratings arrive)."""
    mv = p.get("market_value_eur") or 500_000
    ov = 56 + 7 * math.log(1 + mv / 2.5e6)
    a = age_of(p)
    if a < 23:  # young players' values include potential
        ov -= (23 - a) * 1.2
    if a > 31:  # veterans' values drop faster than their level
        ov += (a - 31) * 1.0
    return max(45, min(93, ov))


def ratings(p):
    grp = POS.get(p.get("position"), ("CM", 9))[0]
    ov = overall(p)
    out = [(ov + SHAPE[grp][i] + jitter(p["name"], i)) * 10 for i in range(10)]
    h = p.get("height_cm") or 180
    out[9] += (h - 182) * 4  # taller -> better in the air
    out[3] += (h - 182) * 3
    gk = [(ov + jitter(p["name"], 10 + i)) * 10 if grp == "GK" else 100 + jitter(p["name"], 20 + i, 40) for i in range(3)]
    return [int(max(50, min(990, x))) for x in out + gk]


def split_name(full):
    parts = full.split()
    if len(parts) == 1:
        return "", parts[0]
    return parts[0], " ".join(parts[1:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--roster", required=True)
    ap.add_argument("--club", required=True)
    ap.add_argument("--team-id", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--long-name")
    ap.add_argument("--short-name")
    ap.add_argument("--stadium")
    ap.add_argument("--captain", help="player name to make captain (default: best senior starter)")
    ap.add_argument("--city")
    ap.add_argument("--copy-kit-from", type=int, help="team id whose kit colours/patterns to copy")
    a = ap.parse_args()

    pl = D.Players(D.load(os.path.join(a.db, "players.dat")))
    ln = D.Links(D.load(os.path.join(a.db, "teamplayerlinks_0.dat")))
    tm = D.Teams(D.load(os.path.join(a.db, "teams.dat")))
    nm = D.TextBank(D.load(os.path.join(a.db, "ftsteamnames.xlc")))
    nat_ids = D.nationality_table(nm)
    nat_alias = {"United States": "USA", "Korea South": "Korea Republic", "Ireland": "Republic of Ireland",
                 "Cote d'Ivoire": "Côte d'Ivoire", "Türkiye": "Turkey", "DR Congo": "DR Congo",
                 "Czech Republic": "Czech Republic", "Bosnia-Herzegovina": "Bosnia and Herzegovina"}

    roster = json.load(open(a.roster))
    club = None
    for lg in roster["leagues"].values():
        if a.club in lg["clubs"]:
            club = lg["clubs"][a.club]["players"]
    if club is None:
        sys.exit(f"club {a.club!r} not in roster")
    squad = sorted(club, key=lambda p: -(p.get("market_value_eur") or 0))[:32]

    # 1) players already in DLS19 keep their own record (and so their face/hair)
    def fold(t):
        return " ".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().split())

    by_name = {}
    for pid, rec in pl.by_id.items():
        q = pl.get(rec)
        by_name.setdefault(fold(f"{q['first_name']} {q['surname']}"), []).append((pid, q))

    def existing(p):
        cands = by_name.get(fold(p["name"]), [])
        if p.get("dob"):
            y = int(p["dob"][:4])
            cands = [c for c in cands if c[1]["birth_year"] in (y, y - 1, y + 1, 1900)]
        return cands[0][0] if len(cands) == 1 else None

    tid = a.team_id
    targets, reused = [None] * len(squad), 0
    for i, p in enumerate(squad):
        pid = existing(p)
        if pid is not None and pid not in targets:
            targets[i], reused = pid, reused + 1
    # 2) everyone else overwrites the slot's old players, then records linked nowhere
    current = [e["player_id"] for e in ln.teams[tid]]
    linked = {e["player_id"] for sq in ln.teams.values() for e in sq}
    pool = [pid for pid in current + [x for x in pl.by_id if x not in linked] if pid not in targets]
    for i in range(len(squad)):
        if targets[i] is None:
            if not pool:
                sys.exit("not enough player records to overwrite")
            targets[i] = pool.pop(0)
            rec = pl.by_id[targets[i]]
            # new face: generic head, neutral defaults until appearance data exists
            pl.set(rec, unk_70=0, unk_72=1, unk_74=0)
    print(f"{reused} players reused their existing DLS19 record (own face)")

    entries, unknown_nat = [], set()
    for p, pid in zip(squad, targets):
        rec = pl.by_id[pid]
        first, last = split_name(p["name"])
        nat_id = D.nationality_id(nat_ids, p.get("nationality"))
        if nat_id is None:
            unknown_nat.add(p.get("nationality") or "?")
        grp, slot = POS.get(p.get("position"), ("CM", 9))
        dob = datetime.date.fromisoformat(p["dob"]) if p.get("dob") else None
        attrs = ratings(p)
        pl.set(rec, first_name=first, surname=last,
               nationality=nat_id if nat_id is not None else pl.get(rec)["nationality"],
               height_cm=p.get("height_cm") or 180,
               weight_kg=int(round((p.get("height_cm") or 180) * 0.42)),
               foot=D.FOOT.get(p.get("foot") or "right", 1),
               pos_primary=slot, pos_secondary=slot, attr=attrs,
               birth_day=dob.day if dob else 1, birth_month=dob.month if dob else 1,
               birth_year=dob.year if dob else 1900)
        entries.append({"p": p, "pid": pid, "slot": slot, "attr": attrs})

    # starting XI by best fit per slot
    used, xi = set(), {}
    for label, code in XI_SLOTS:
        cands = [e for e in entries if e["pid"] not in used and e["p"].get("position") in SLOT_FITS[label]]
        if not cands:  # fall back to anyone outfield
            cands = [e for e in entries if e["pid"] not in used and e["p"].get("position") != "Goalkeeper"]
        best = max(cands, key=lambda e: overall(e["p"]))
        used.add(best["pid"])
        xi[best["pid"]] = code

    starters = [e for e in entries if e["pid"] in xi]
    outfield = [e for e in starters if e["slot"] != 0]
    captain = max(outfield, key=lambda e: (age_of(e["p"]) >= 25, overall(e["p"])))
    if a.captain:
        named = [e for e in entries if e["p"]["name"].lower() == a.captain.lower()]
        if not named:
            sys.exit(f"captain {a.captain!r} not in squad")
        captain = named[0]
    pen = max(outfield, key=lambda e: e["attr"][6])
    fk = max(outfield, key=lambda e: e["attr"][7] + e["attr"][6])
    corner = max(outfield, key=lambda e: e["attr"][7])

    taken = {int(e["p"]["shirt"]) for e in entries if str(e["p"].get("shirt") or "").isdigit()}
    free = (n for n in range(2, 99) if n not in taken)
    squad_links = []
    for e in sorted(entries, key=lambda e: (e["pid"] not in xi, XI_SLOTS.index(next(s for s in XI_SLOTS if s[1] == xi[e["pid"]])) if e["pid"] in xi else 0)):
        shirt = int(e["p"]["shirt"]) if str(e["p"].get("shirt") or "").isdigit() else (1 if e["slot"] == 0 and 1 not in taken else next(free))
        taken.add(shirt)
        flags = 0
        if e["pid"] in xi:
            flags |= D.FLAG_STARTER
        if e is captain:
            flags |= D.FLAG_CAPTAIN
        if e is pen:
            flags |= D.FLAG_PEN
        if e is fk:
            flags |= D.FLAG_FK
        if e is corner:
            flags |= D.FLAG_CORNER_L | D.FLAG_CORNER_R
        squad_links.append({"shirt": shirt, "slot": xi.get(e["pid"], e["slot"]), "flags": flags, "player_id": e["pid"]})
    ln.teams[tid] = squad_links
    tm.set_setpieces(tid, captain["pid"], fk["pid"], corner["pid"], pen["pid"], corner["pid"])

    if a.long_name:
        nm.set(f"TXT_TEAMNAMELONG_{tid}", a.long_name)
        nm.set(f"TXT_TEAMNAMEMED_{tid}", a.long_name)
    if a.short_name:
        nm.set(f"TXT_TEAMNAMESHORT_{tid}", a.short_name)
    if a.stadium:
        tm.set_stadium(tid, a.stadium)
    if a.city:
        nm.set(f"TXT_TEAMNAMECITY_{tid}", a.city)
    if a.copy_kit_from is not None:
        tm.copy_kit(a.copy_kit_from, tid)

    os.makedirs(a.out, exist_ok=True)
    D.save_zlib(os.path.join(a.out, "players.dat"), pl.to_bytes())
    D.save_zlib(os.path.join(a.out, "teamplayerlinks_0.dat"), ln.to_bytes())
    D.save_zlib(os.path.join(a.out, "teams.dat"), tm.to_bytes())
    open(os.path.join(a.out, "ftsteamnames.xlc"), "wb").write(nm.to_bytes())

    print(f"wrote {len(squad_links)} players into team {tid} ({nm.get(f'TXT_TEAMNAMELONG_{tid}')})")
    for l in squad_links:
        e = next(x for x in entries if x["pid"] == l["player_id"])
        tag = "XI" if l["flags"] & 1 else "  "
        print(f"  {tag} #{l['shirt']:>2} slot {l['slot']:>2} flags {l['flags']:#04x}  {e['p']['name']:<24} ov~{overall(e['p']):.0f}")
    if unknown_nat:
        print("nationalities not in DLS19 (kept the old record's):", sorted(unknown_nat))


if __name__ == "__main__":
    main()
