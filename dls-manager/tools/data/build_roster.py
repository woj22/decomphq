#!/usr/bin/env python3
"""Merge squad sources into one 2026/27 roster (data/roster_2026_27.json).

Priority per club:
  1. user-supplied CSVs (club,player,position,age,nationality,contract_expiry,market_value_eur)
  2. Wikipedia current squads (squads.json from fetch_wikipedia_squads.py)
Every player is then enriched from the open transfermarkt-datasets players export
(date of birth, height, preferred foot, citizenship, market value) by name match.

Usage:
  python3 -I build_roster.py --wiki <wp_out_dir> --tm-players <players.csv.gz> \
      --user-csv <dir or files...> --out <data_dir>
"""
import argparse
import csv
import datetime
import glob
import gzip
import io
import json
import os
import re
import unicodedata

LEAGUE_OF = {"premier_league": "Premier League", "la_liga": "LaLiga", "prvaliga": "PrvaLiga"}


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def club_key(name):
    drop = {"fc", "f", "c", "a", "afc", "cf", "ud", "cd", "rcd", "sd", "rc", "ca", "nk", "ns", "club", "de", "futbol"}
    toks = [t for t in fold(name) if t not in drop]
    return " ".join(toks)


def person_key(name):
    return " ".join(fold(name))


def parse_money(v):
    v = (v or "").strip().replace("€", "").replace(",", "")
    m = re.match(r"([\d.]+)\s*([mk]?)", v, re.I)
    if not m:
        return None
    n = float(m.group(1))
    return int(n * {"m": 1e6, "k": 1e3, "": 1}[m.group(2).lower()])


CLUB_ALIASES = {
    "deportivo": "Deportivo de A Coruña",
    "athletic": "Athletic Bilbao",
    "atletico": "Atlético Madrid",
    "rayo": "Rayo Vallecano",
    "racing": "Racing de Santander",
    "alaves": "Deportivo Alavés",
}

POS_ABBR = {"GK": "Goalkeeper", "CB": "Centre-Back", "LB": "Left-Back", "RB": "Right-Back",
            "DM": "Defensive Midfield", "CM": "Central Midfield", "AM": "Attacking Midfield",
            "LM": "Left Midfield", "RM": "Right Midfield", "LW": "Left Winger", "RW": "Right Winger",
            "SS": "Second Striker", "CF": "Centre-Forward"}


def dmy_to_iso(v):
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", v or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def normalize_user_row(r):
    """Accept both supplied layouts and return one dict per player."""
    g = lambda *keys: next(((r.get(k) or "").strip() for k in keys if (r.get(k) or "").strip()), "")
    pos = g("position")
    h = g("height").replace(",", ".").rstrip("m").strip()
    try:
        height = int(round(float(h) * 100)) if h else None
    except ValueError:
        height = None
    age = g("age")
    return {
        "club": g("club"),
        "name": g("player"),
        "shirt": g("shirt") or None,
        "position": POS_ABBR.get(pos.upper(), pos),
        "age": int(age) if age.isdigit() else None,
        "dob": dmy_to_iso(g("DOB", "dob", "date_of_birth")),
        "nationality": g("nationality"),
        "height_cm": height,
        "foot": g("foot").lower() or None,
        "joined": dmy_to_iso(g("joined")),
        "signed_from": g("signed_from") or None,
        "contract_expiry": g("contract_until", "contract_expiry") or None,
        "market_value_eur": parse_money(g("market_value", "market_value_eur")),
    }


WIKI_POS = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfield", "FW": "Attack"}


def load_tm(path):
    """name key -> list of TM player rows (several players can share a name)."""
    by_name = {}
    for p in csv.DictReader(gzip.open(path, "rt", encoding="utf-8")):
        by_name.setdefault(person_key(p["name"]), []).append(p)
    return by_name


def age_on(dob, ref=datetime.date(2026, 11, 17)):
    try:
        d = datetime.date.fromisoformat(dob[:10])
    except (TypeError, ValueError):
        return None
    return ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))


def tm_lookup(tm, name, age=None):
    k = person_key(name)
    cands = list(tm.get(k, []))
    toks = k.split()
    if not cands and len(toks) >= 2:  # "first last" against longer TM names
        cands = [v for kk, vs in tm.items() if kk.split()[0] == toks[0] and kk.split()[-1] == toks[-1] for v in vs]
    if age is not None:  # drop namesakes whose age does not fit
        cands = [c for c in cands if (a := age_on(c["date_of_birth"])) is not None and abs(a - age) <= 1]
    if not cands:
        return None
    if len(cands) > 1 and age is None:
        return None  # ambiguous name and nothing to tell them apart
    return max(cands, key=lambda c: (c["last_season"], c["market_value_in_eur"] or "0"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--tm-players", required=True)
    ap.add_argument("--user-csv", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    squads = json.load(open(os.path.join(a.wiki, "squads.json")))
    tm = load_tm(a.tm_players)

    files = []
    for f in a.user_csv:
        files += sorted(glob.glob(os.path.join(f, "*"))) if os.path.isdir(f) else [f]
    user_rows = []
    for f in files:
        text = open(f, encoding="utf-8-sig").read()
        delim = "|" if text.split("\n", 1)[0].count("|") > text.split("\n", 1)[0].count(",") else ","
        user_rows += [normalize_user_row(r) for r in csv.DictReader(io.StringIO(text), delimiter=delim)]

    clubs = {}  # canonical title -> league
    for lg, cl in squads.items():
        for c in cl:
            clubs[c] = lg
    key_to_club = {club_key(c): c for c in clubs}

    def find_club(name):
        k = club_key(name)
        if k in key_to_club:
            return key_to_club[k]
        if k in CLUB_ALIASES:
            return CLUB_ALIASES[k]
        hits = [c for kk, c in key_to_club.items() if set(k.split()) <= set(kk.split())]
        return hits[0] if len(hits) == 1 else None

    user_by_club, unmatched_clubs = {}, set()
    for r in user_rows:
        c = find_club(r["club"])
        if not c:
            unmatched_clubs.add(r["club"])
            continue
        user_by_club.setdefault(c, []).append(r)

    roster = {"season": "2026/27", "leagues": {}}
    report = []
    for lg, cl in squads.items():
        out_cl = {}
        for c in cl:
            players = []
            if c in user_by_club:
                src = "user"
                for r in user_by_club[c]:
                    players.append({k: v for k, v in r.items() if k != "club" and v not in (None, "")})
            else:
                src = "wikipedia"
                for r in squads[lg][c]:
                    players.append({"name": r["name"], "position": WIKI_POS.get(r["pos"].upper(), r["pos"]),
                                    "shirt": r["no"] or None, "nat_code": r["nat"]})
            matched = 0
            for p in players:
                t = tm_lookup(tm, p["name"], p.get("age"))
                if t:
                    matched += 1
                    p["tm_id"] = int(t["player_id"])
                    p.setdefault("dob", (t["date_of_birth"] or "")[:10] or None)
                    p.setdefault("height_cm", int(t["height_in_cm"]) if t["height_in_cm"] else None)
                    p.setdefault("foot", t["foot"] or None)
                    p.setdefault("nationality", t["country_of_citizenship"])
                    if not p.get("market_value_eur") and t["market_value_in_eur"]:
                        p["market_value_eur"] = int(float(t["market_value_in_eur"]))
                    if p["position"] in WIKI_POS.values() and t["sub_position"]:
                        p["position"] = t["sub_position"]
            out_cl[c] = {"source": src, "players": players}
            report.append((lg, c, src, len(players), matched))
        roster["leagues"][lg] = {"name": LEAGUE_OF[lg], "clubs": out_cl}

    os.makedirs(a.out, exist_ok=True)
    json.dump(roster, open(os.path.join(a.out, "roster_2026_27.json"), "w"), ensure_ascii=False, indent=1)
    for lg, c, src, n, m in report:
        print(f"{lg:15s} {c:32s} {src:9s} {n:3d} players, {m:3d} matched to TM data")
    if unmatched_clubs:
        print("user clubs not matched to a 2026/27 league club:", sorted(unmatched_clubs))


if __name__ == "__main__":
    main()
