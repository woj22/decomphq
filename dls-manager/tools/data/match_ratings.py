#!/usr/bin/env python3
"""Match an EA FC ratings export to the 2026/27 roster.

Input: the owner's sheet export (CSV) with two side-by-side tables
  A-C: Premier League club, "Surname, Given names", overall
  E-G: LaLiga club, "Surname, Given names", overall
Files exported from Google Sheets sometimes arrive double-encoded (MbappÃ©); that is undone.

Matching is done within each club first (player names are legal names, the roster uses
common names, so tokens are compared accent-insensitively with nickname-friendly fuzzy
rules), then unmatched players are tried against the other clubs of the same league
(for late transfers). Women's players share club names in the export; they simply find
no partner in the men's roster.

Output: data/ratings_2026_27.json  {roster club: {roster player name: overall}}
        and a report of roster players left without a rating.

Usage: python3 -I match_ratings.py <export.csv> --roster data/roster_2026_27.json --out data/ratings_2026_27.json
"""
import argparse
import csv
import difflib
import json
import re
import unicodedata

EA_CLUB = {  # EA name -> roster club key
    "Arsenal": "Arsenal F.C.", "Aston Villa": "Aston Villa F.C.", "AFC Bournemouth": "AFC Bournemouth",
    "Brentford": "Brentford F.C.", "Brighton": "Brighton & Hove Albion F.C.", "Chelsea": "Chelsea F.C.",
    "Coventry City": "Coventry City F.C.", "Crystal Palace": "Crystal Palace F.C.", "Everton": "Everton F.C.",
    "Fulham": "Fulham F.C.", "Hull City": "Hull City A.F.C.", "Ipswich": "Ipswich Town F.C.",
    "Leeds United": "Leeds United F.C.", "Liverpool": "Liverpool F.C.", "Man Utd": "Manchester United F.C.",
    "Manchester City": "Manchester City F.C.", "Newcastle Utd": "Newcastle United F.C.",
    "Nott'm Forest": "Nottingham Forest F.C.", "Spurs": "Tottenham Hotspur F.C.", "Sunderland": "Sunderland A.F.C.",
    "Athletic Club": "Athletic Bilbao", "Atlético de Madrid": "Atlético Madrid", "CA Osasuna": "CA Osasuna",
    "D. Alavés": "Deportivo Alavés", "Elche CF": "Elche CF", "FC Barcelona": "FC Barcelona", "Getafe CF": "Getafe CF",
    "Levante UD": "Levante UD", "Málaga CF": "Málaga CF", "R. Racing Club": "Racing de Santander",
    "RC Celta": "RC Celta de Vigo", "RC Deportivo": "Deportivo de A Coruña", "RCD Espanyol": "RCD Espanyol",
    "Rayo Vallecano": "Rayo Vallecano", "Real Betis": "Real Betis", "Real Madrid": "Real Madrid CF",
    "Real Sociedad": "Real Sociedad", "Sevilla FC": "Sevilla FC", "Valencia CF": "Valencia CF",
    "Villarreal CF": "Villarreal CF",
}


def fold(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("ø", "o").replace("ß", "ss")
    return re.sub(r"[^a-z ]+", " ", s).split()


def read_export(path):
    raw = open(path, "rb").read().decode("utf-8-sig")
    if "Ã" in raw or "Â" in raw:  # UTF-8 that was read as Windows-1252 somewhere: undo it
        def back(ch):
            try:
                return ch.encode("cp1252")
            except UnicodeEncodeError:
                return ch.encode("latin-1", errors="replace")  # bytes 0x81/0x8D/0x8F/0x90/0x9D
        raw = b"".join(back(ch) for ch in raw).decode("utf-8", errors="replace")
    rows = []
    for r in csv.reader(raw.splitlines()):
        for c0 in (0, 4):
            if len(r) > c0 + 2 and r[c0].strip() and r[c0 + 2].strip().isdigit():
                rows.append((r[c0].strip(), r[c0 + 1].strip(), int(r[c0 + 2])))
    return rows


def ea_tokens(name):
    last, _, first = name.partition(",")
    return fold(last), fold(first)


# common short forms -> legal given names (folded)
NICK = {
    "kike": {"enrique"}, "riki": {"enrique", "ricardo"}, "fran": {"francisco"}, "paco": {"francisco"},
    "kiko": {"francisco"}, "alex": {"alejandro", "alexander", "alexandre"}, "toni": {"antonio", "anthony"},
    "dan": {"daniel"}, "dani": {"daniel"}, "ben": {"benjamin"}, "jonny": {"jonathan", "jonatan"},
    "johnny": {"joao", "john", "jonathan"}, "isi": {"isaac"}, "moi": {"moises"}, "pep": {"josep"},
    "rafita": {"rafael"}, "rafa": {"rafael"}, "manu": {"manuel", "jose"}, "ximo": {"joaquin"},
    "edu": {"eduardo"}, "buba": {"aboubacar"}, "abde": {"abderrahman", "abdessamad"}, "nico": {"nicolas", "nicholas"},
    "chema": {"jose"}, "tete": {"jose"}, "cucho": {"juan"}, "peque": {"gerard"}, "pepe": {"jose"},
    "nacho": {"ignacio", "jose"}, "javi": {"javier"}, "migue": {"miguel"}, "santi": {"santiago"},
    "kostas": {"konstantinos"}, "konstantinos": {"kostas"}, "yegor": {"yehor"}, "mykhaylo": {"mykhailo"},
    "jota": {"joao", "jose"}, "pablo": {"pablo"}, "iñaki": {"inaki"}, "jon": {"jon"}, "unai": {"unai"},
}
# one-word nicknames whose legal names share nothing distinctive with them: (given, family) folded
SINGLE_NICK = {
    "pedri": ("pedro", "gonzalez"), "raphinha": ("raphael", "dias"), "koke": ("jorge", "resurreccion"),
    "isco": ("francisco", "alarcon"), "angelino": ("jose", "esmoris"), "juanmi": ("juan", "jimenez"),
    "davinchi": ("david", "cordon"),
}
GENERIC = {"juan", "jose", "angel", "david", "daniel", "carlos", "luis", "pedro", "pablo", "manuel", "antonio",
           "francisco", "javier", "miguel", "alejandro", "jorge", "sergio", "marc", "maria"}


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def first_ok(r_first, ea_first, ea_last):
    if not ea_first:  # export gave only one name
        return True
    if r_first in ea_first:
        return True
    if NICK.get(r_first, set()) & set(ea_first):
        return True
    return any(ratio(r_first, x) >= 0.8 and x not in GENERIC for x in ea_first)


def score(roster_name, ea_name):
    rt = fold(roster_name)
    last, first = ea_tokens(ea_name)
    alltok = set(last + first)
    if not rt:
        return 0
    if len(rt) == 1:  # single-name players: Pedri, Gabriel, Rodrygo, Estêvão
        t = rt[0]
        if t in SINGLE_NICK:  # famous nicknames: must match the legal given name AND family name
            given, family = SINGLE_NICK[t]
            return 3 if given in first and family in last else 0
        if t in alltok:
            return 3
        # nickname close to a given/family name (Pedri~Pedro, Gavi~Gavira) but never via generic names
        if any(len(t) >= 4 and x[:4] == t[:4] and ratio(t, x) >= 0.75 and x not in GENERIC for x in alltok):
            return 2
        return 0
    surname = rt[-1]
    s = 0.0
    if surname in last or " ".join(rt[1:]) in " ".join(last):
        s += 3
    elif surname in alltok:
        s += 2
    elif any(ratio(surname, x) > 0.85 for x in last):
        s += 2
    else:
        return 0
    if not first_ok(rt[0], first, last):
        return 0  # same surname, different person (often a women's-team player)
    s += 1.5
    s += ratio(" ".join(rt), " ".join(first + last)) * 0.5
    return s


def assign(roster_players, ea_rows, min_score):
    pairs = []
    for i, rp in enumerate(roster_players):
        for j, (_, en, ov) in enumerate(ea_rows):
            sc = score(rp, en)
            if sc >= min_score:
                pairs.append((sc, i, j))
    pairs.sort(reverse=True)
    used_r, used_e, out = set(), set(), {}
    for sc, i, j in pairs:
        if i in used_r or j in used_e:
            continue
        used_r.add(i)
        used_e.add(j)
        out[i] = j
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export")
    ap.add_argument("--roster", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = read_export(a.export)
    roster = json.load(open(a.roster))
    by_club = {}
    for club, name, ov in rows:
        if club in EA_CLUB:
            by_club.setdefault(EA_CLUB[club], []).append((club, name, ov))
    league_of = {c: lg for lg, v in roster["leagues"].items() for c in v["clubs"]}

    result, unmatched, leftovers = {}, [], {}
    for club, ea in by_club.items():
        players = [p["name"] for p in roster["leagues"][league_of[club]]["clubs"][club]["players"]]
        m = assign(players, ea, 2.0)
        result[club] = {players[i]: ea[j][2] for i, j in m.items()}
        leftovers[club] = [e for j, e in enumerate(ea) if j not in m.values()]
        unmatched += [(club, players[i]) for i in range(len(players)) if i not in m]

    # second pass: transfers inside the same league, strict score
    still = []
    for club, name in unmatched:
        lg = league_of[club]
        best = None
        for oc, rest in leftovers.items():
            if league_of[oc] != lg or oc == club:
                continue
            for e in rest:
                sc = score(name, e[1])
                if sc >= 4.0 and (best is None or sc > best[0]):
                    best = (sc, oc, e)
        if best:
            result[club][name] = best[2][2]
            leftovers[best[1]].remove(best[2])
        else:
            still.append((club, name))

    json.dump(result, open(a.out, "w"), ensure_ascii=False, indent=1)
    total = sum(len(roster["leagues"][league_of[c]]["clubs"][c]["players"]) for c in by_club)
    got = sum(len(v) for v in result.values())
    print(f"{len(rows)} export rows, {len(by_club)} clubs; rated {got}/{total} roster players -> {a.out}")
    for club in sorted(by_club):
        miss = [n for c, n in still if c == club]
        if miss:
            print(f"  {club}: no rating for {', '.join(miss)}")


if __name__ == "__main__":
    main()
