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
import glob
import gzip
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


WIKI_POS = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfield", "FW": "Attack"}


def load_tm(path):
    by_name = {}
    for p in csv.DictReader(gzip.open(path, "rt", encoding="utf-8")):
        k = person_key(p["name"])
        # keep the most recent record per name
        if k not in by_name or p["last_season"] > by_name[k]["last_season"]:
            by_name[k] = p
    return by_name


def tm_lookup(tm, name, club_hint=""):
    k = person_key(name)
    if k in tm:
        return tm[k]
    toks = k.split()
    if len(toks) >= 2:  # try "first last" against longer TM names
        cands = [v for kk, v in tm.items() if kk.split()[-1] == toks[-1] and kk.split()[0] == toks[0]]
        if len(cands) == 1:
            return cands[0]
    return None


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
        user_rows += list(csv.DictReader(open(f, encoding="utf-8-sig")))

    clubs = {}  # canonical title -> league
    for lg, cl in squads.items():
        for c in cl:
            clubs[c] = lg
    key_to_club = {club_key(c): c for c in clubs}

    user_by_club, unmatched_clubs = {}, set()
    for r in user_rows:
        c = key_to_club.get(club_key(r["club"]))
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
                    players.append({"name": r["player"].strip(), "position": r["position"].strip(),
                                    "age": int(r["age"]) if r.get("age", "").strip().isdigit() else None,
                                    "nationality": r["nationality"].strip(),
                                    "contract_expiry": r.get("contract_expiry", "").strip() or None,
                                    "market_value_eur": parse_money(r.get("market_value_eur"))})
            else:
                src = "wikipedia"
                for r in squads[lg][c]:
                    players.append({"name": r["name"], "position": WIKI_POS.get(r["pos"].upper(), r["pos"]),
                                    "shirt": r["no"] or None, "nat_code": r["nat"]})
            matched = 0
            for p in players:
                t = tm_lookup(tm, p["name"])
                if t:
                    matched += 1
                    p["tm_id"] = int(t["player_id"])
                    p["dob"] = (t["date_of_birth"] or "")[:10] or None
                    p["height_cm"] = int(t["height_in_cm"]) if t["height_in_cm"] else None
                    p["foot"] = t["foot"] or None
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
