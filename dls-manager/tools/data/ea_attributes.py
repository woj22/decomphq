#!/usr/bin/env python3
"""Give every player a realistic attribute profile from EA SPORTS FC's public ratings.

The ratings database (drop-api.ea.com, fetched once into a JSON file) has each FC player's
sub-attributes. They are turned into DLS's 13 attributes:

    speed    = sprint speed               accel    = acceleration
    stamina  = stamina                    strength = strength
    tackling = standing/sliding tackle, interceptions, defensive awareness
    control  = ball control, dribbling    shooting = finishing, shot power, long shots, positioning
    passing  = short/long passing, vision crossing = crossing
    heading  = heading accuracy, jumping
    GK       = reflexes + diving, handling, positioning + kicking

Players found in FC (same birth date and a matching name, or the same full name in the same
league) get their own profile. Everyone else (the Slovenian leagues aren't in FC) gets the
profile of a real FC player at the same position and a similar overall, chosen per player,
with small individual differences and adjustments for height and age.

The overall is left alone: run calibrate_ratings.py afterwards so DLS's overall formula still
gives each player's rating. Adds "pot" (potential) where the data has none yet.

Usage: python3 -I ea_attributes.py --ea ea_full.json --data menu/data.json
"""
import argparse
import datetime
import hashlib
import json
import random
import unicodedata

POS_EA = {"GK": ["GK"], "CB": ["CB"], "LB": ["LB", "LWB"], "RB": ["RB", "RWB"], "DM": ["CDM"], "CM": ["CM"],
          "AM": ["CAM"], "LM": ["LM", "LW"], "RM": ["RM", "RW"], "LW": ["LW", "LM"], "RW": ["RW", "RM"],
          "SS": ["CF", "ST", "CAM"], "ST": ["ST", "CF"]}
LEAGUE_EA = {"premier_league": "Premier League", "la_liga": "LALIGA EA SPORTS"}


def fold(t):
    t = unicodedata.normalize("NFKD", t or "")
    return " ".join("".join(ch for ch in t if not unicodedata.combining(ch)).lower().replace("-", " ").replace(".", " ").split())


def to_dls(s):
    def v(k, d=50):
        x = s.get(k)
        return d if x is None else x
    a = [v("sprintSpeed"), v("acceleration"), v("stamina"), v("strength"),
         .45 * v("standingTackle") + .25 * v("slidingTackle") + .15 * v("interceptions") + .15 * v("defensiveAwareness"),
         .6 * v("ballControl") + .4 * v("dribbling"),
         .55 * v("finishing") + .2 * v("shotPower") + .15 * v("longShots") + .1 * v("positioning"),
         .55 * v("shortPassing") + .25 * v("longPassing") + .2 * v("vision"),
         v("crossing"), .75 * v("headingAccuracy") + .25 * v("jumping"),
         .6 * v("gkReflexes") + .4 * v("gkDiving"), v("gkHandling"), .7 * v("gkPositioning") + .3 * v("gkKicking")]
    return [max(1, min(99, round(x))) for x in a]


def ea_dob(s):
    try:
        return datetime.datetime.strptime(s.split()[0], "%m/%d/%Y").date().isoformat()
    except Exception:
        return None


def potential(p, rnd):
    """Estimate until real potentials arrive: young players have room to grow."""
    age, ovr = p.get("age") or 25, p["ovr"]
    room = 18 if age <= 17 else 15 if age <= 19 else 11 if age <= 21 else 7 if age <= 23 else 4 if age <= 25 else 2 if age <= 27 else 0
    return min(95, ovr + max(0, round(room * (0.55 + rnd.random() * 0.7))))


def index(ea):
    by_dob, by_name = {}, {}
    for e in ea:
        e["dobi"] = ea_dob(e.get("dob") or "")
        names = {fold((e.get("fn") or "") + " " + (e.get("ln") or "")), fold(e.get("cn") or ""), fold(e.get("ln") or "")}
        e["names"] = {n for n in names if n}
        if e["dobi"]:
            by_dob.setdefault(e["dobi"], []).append(e)
        for n in e["names"]:
            by_name.setdefault(n, []).append(e)
    return by_dob, by_name


def find(p, league, by_dob, by_name):
    """The player's FC entry: same birth date and a matching name, or a unique full-name match in the league."""
    nm = fold(p["name"])
    toks = set(nm.split())
    for e in by_dob.get(p.get("dob") or "", []):
        if nm in e["names"] or toks & set(" ".join(e["names"]).split()):
            return e
    if league in LEAGUE_EA:
        cands = [e for e in by_name.get(nm, []) if e.get("league") == LEAGUE_EA[league]]
        if len(cands) == 1:
            return cands[0]
    return None


EA_POS = {"GK": "GK", "CB": "CB", "LB": "LB", "LWB": "LB", "RB": "RB", "RWB": "RB", "CDM": "DM", "CM": "CM",
          "CAM": "AM", "LM": "LM", "RM": "RM", "LW": "LW", "RW": "RW", "CF": "SS", "ST": "ST"}


def ea_positions(path, data):
    """Player id -> primary position in FC (menu codes), for players found in the ratings."""
    ea = [e for e in json.load(open(path)) if e.get("s")]
    by_dob, by_name = index(ea)
    leagues = {c: v["league"] for c, v in data["clubs"].items()}
    out = {}
    for p in data["players"]:
        e = find(p, leagues[p["club"]], by_dob, by_name)
        if e and e.get("pos") in EA_POS:
            out[p["id"]] = EA_POS[e["pos"]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ea", required=True)
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    ea = [e for e in json.load(open(a.ea)) if e.get("s") and e["s"].get("sprintSpeed") is not None]
    by_dob = {}
    by_name = {}
    for e in ea:
        e["dobi"] = ea_dob(e.get("dob") or "")
        names = {fold((e.get("fn") or "") + " " + (e.get("ln") or "")), fold(e.get("cn") or ""), fold(e.get("ln") or "")}
        e["names"] = {n for n in names if n}
        if e["dobi"]:
            by_dob.setdefault(e["dobi"], []).append(e)
        for n in e["names"]:
            by_name.setdefault(n, []).append(e)
    by_pos = {}
    for e in ea:
        by_pos.setdefault(e["pos"], []).append(e)

    data = json.load(open(a.data, encoding="utf-8"))
    leagues = {c: v["league"] for c, v in data["clubs"].items()}
    real = arche = 0
    for p in data["players"]:
        rnd = random.Random(int(hashlib.sha1(p["name"].encode()).hexdigest()[:8], 16))
        nm = fold(p["name"])
        toks = set(nm.split())
        hit = None
        for e in by_dob.get(p.get("dob") or "", []):
            if nm in e["names"] or toks & set(" ".join(e["names"]).split()):
                hit = e
                break
        if hit is None and leagues[p["club"]] in LEAGUE_EA:
            cands = [e for e in by_name.get(nm, []) if e.get("league") == LEAGUE_EA[leagues[p["club"]]]]
            if len(cands) == 1:
                hit = cands[0]
        if hit is not None:
            p["attrs"] = to_dls(hit["s"])
            p["attrSource"] = "fc"
            real += 1
        else:
            # a real FC player at the same position and a similar level as the template
            pool = []
            for pos in POS_EA.get(p["pos"], ["CM"]):
                pool += by_pos.get(pos, [])
            target = max(47, p["ovr"])
            near = [e for e in pool if abs(e["ovr"] - target) <= 2] or [e for e in pool if abs(e["ovr"] - target) <= 5] or pool
            t = to_dls(rnd.choice(near)["s"])
            t = [x + rnd.randint(-3, 3) for x in t]
            h = p.get("height")
            if h:
                d = max(-8, min(8, h - 182))
                t[9] += round(d * 0.5); t[3] += round(d * 0.4); t[0] -= round(d * 0.3); t[1] -= round(d * 0.4)
            age = p.get("age") or 25
            if age > 30:
                t[0] -= (age - 30) * 2; t[1] -= (age - 30) * 2; t[2] -= age - 30
            p["attrs"] = [max(1, min(99, x)) for x in t]
            p["attrSource"] = "profile"
            arche += 1
        if p.get("pot") is None:
            p["pot"] = potential(p, rnd)
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{real} players with their own FC attributes, {arche} with a position profile")


if __name__ == "__main__":
    main()
