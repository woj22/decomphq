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

# leagues that only come from user files (not on the Wikipedia season pages we fetch)
USER_LEAGUES = {"2. SNL": "slovenia_2snl", "3. SNL": "slovenia_2snl"}
USER_LEAGUE_NAMES = {"slovenia_2snl": "2. SNL"}

POS_ABBR = {"GK": "Goalkeeper", "CB": "Centre-Back", "LB": "Left-Back", "RB": "Right-Back",
            "DM": "Defensive Midfield", "CM": "Central Midfield", "AM": "Attacking Midfield",
            "LM": "Left Midfield", "RM": "Right Midfield", "LW": "Left Winger", "RW": "Right Winger",
            "SS": "Second Striker", "CF": "Centre-Forward",
            "MIDFIELDER": "Central Midfield", "STRIKER": "Centre-Forward", "DEFENDER": "Centre-Back"}


def dmy_to_iso(v):
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", v or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def normalize_user_row(r):
    """Accept both supplied layouts and return one dict per player."""
    g = lambda *keys: next(((r.get(k) or "").strip() for k in keys if (r.get(k) or "").strip()), "")
    pos = g("position")
    h = g("height", "height_cm").replace(",", ".").rstrip("m").strip()
    try:
        height = float(h) if h else None
        height = int(round(height * 100)) if height and height < 3 else (int(height) if height else None)
    except ValueError:
        height = None
    age = g("age")
    return {
        "club": g("club"),
        "name": g("player"),
        "shirt": g("shirt", "shirt_number") or None,
        "league": g("league") or None,
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


LEFT_FOOT_P = {  # chance of being left-footed by position (left-sided roles are mostly left-footed)
    "Left-Back": 0.65, "Left Winger": 0.45, "Left Midfield": 0.5, "Right Winger": 0.3,
    "Right Midfield": 0.2, "Right-Back": 0.08, "Centre-Back": 0.22, "Goalkeeper": 0.2,
    "Defensive Midfield": 0.2, "Central Midfield": 0.2, "Attacking Midfield": 0.25,
    "Second Striker": 0.25, "Centre-Forward": 0.22,
}


def estimate_foot(name, position):
    """Deterministic pseudo-random foot so reruns give the same answer."""
    import hashlib
    r = int(hashlib.sha1(name.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    if r < 0.03:
        return "both"
    return "left" if r < 0.03 + LEFT_FOOT_P.get(position, 0.22) * 0.97 else "right"


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
    user_rows, seen, skipped = [], set(), []
    for f in files:
        text = open(f, encoding="utf-8-sig").read()
        delim = "|" if text.split("\n", 1)[0].count("|") > text.split("\n", 1)[0].count(",") else ","
        for r in csv.DictReader(io.StringIO(text), delimiter=delim):
            vals = "".join(v or "" for v in r.values() if isinstance(v, str))
            if "\uff5c" in vals or not (r.get("player") or "").strip():
                skipped.append((os.path.basename(f), r.get("club"), r.get("player")))
                continue
            row = normalize_user_row(r)
            key = (club_key(row["club"]), person_key(row["name"]))
            if key in seen:
                continue
            seen.add(key)
            user_rows.append(row)

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
        if len(hits) != 1:
            hits = [c for kk, c in key_to_club.items() if kk and set(kk.split()) <= set(k.split())]
        return hits[0] if len(hits) == 1 else None

    user_by_club, unmatched_clubs = {}, set()
    for r in user_rows:
        c = find_club(r["club"])
        if not c and r.get("league") in USER_LEAGUES:
            lg = USER_LEAGUES[r["league"]]
            squads.setdefault(lg, {}).setdefault(r["club"], [])
            clubs[r["club"]] = lg
            key_to_club[club_key(r["club"])] = r["club"]
            c = r["club"]
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
                wiki_shirts = {person_key(w["name"]): w["no"] for w in squads[lg][c] if w.get("no")}
                for r in user_by_club[c]:
                    p = {k: v for k, v in r.items() if k not in ("club", "league") and v not in (None, "")}
                    if "shirt" not in p and person_key(p["name"]) in wiki_shirts:
                        p["shirt"] = wiki_shirts[person_key(p["name"])]  # fill from Wikipedia squad list
                    players.append(p)
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
            for p in players:
                if not p.get("foot"):
                    p["foot"] = estimate_foot(p["name"], p.get("position"))
                    p["foot_estimated"] = True
            out_cl[c] = {"source": src, "players": players}
            report.append((lg, c, src, len(players), matched))
        roster["leagues"][lg] = {"name": LEAGUE_OF.get(lg) or USER_LEAGUE_NAMES.get(lg, lg), "clubs": out_cl}

    os.makedirs(a.out, exist_ok=True)
    json.dump(roster, open(os.path.join(a.out, "roster_2026_27.json"), "w"), ensure_ascii=False, indent=1)
    for lg, c, src, n, m in report:
        print(f"{lg:15s} {c:32s} {src:9s} {n:3d} players, {m:3d} matched to TM data")
    if skipped:
        print(f"skipped {len(skipped)} damaged/empty rows:", skipped[:5])
    if unmatched_clubs:
        print("user clubs not matched to a 2026/27 league club:", sorted(unmatched_clubs))


if __name__ == "__main__":
    main()
