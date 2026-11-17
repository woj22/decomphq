#!/usr/bin/env python3
"""Export the roster as the manager menu's game data (menu/data.json).

Adds per-player ratings (same estimate as tools/db/build_team.py, with a league-level
fallback when no market value exists), club display names from tools/db/slot_map.json,
and club colours from the cached Wikipedia club pages (infobox kit colours).

Usage: python3 -I export_game_data.py --roster data/roster_2026_27.json \
           --wiki-pages <wp_dir>/pages --out menu/data.json
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "db"))
import build_team as B  # noqa: E402

TODAY = datetime.date(2026, 8, 1)  # season start for ages
LEAGUE_ORDER = ["premier_league", "la_liga", "prvaliga", "slovenia_2snl"]
LEAGUE_META = {
    "premier_league": {"name": "Premier League", "country": "England", "short": "PL", "cycles": 2, "base": 66},
    "la_liga": {"name": "LaLiga", "country": "Spain", "short": "LL", "cycles": 2, "base": 65},
    "prvaliga": {"name": "PrvaLiga", "country": "Slovenia", "short": "PRVA", "cycles": 4, "base": 60},
    "slovenia_2snl": {"name": "2. SNL", "country": "Slovenia", "short": "2SNL", "cycles": 2, "base": 53},
}
# Wikipedia page titles for 2. SNL clubs (roster name -> page)
WIKI_TITLE = {
    "NK Vrhnika": "NK Vrhnika", "NK Krka": "NK Krka", "ND Primorje": "ND Primorje", "NK Dekani": "NK Dekani",
    "NK Jesenice": "NK Jesenice", "ND Dravinja Kostroj": "NK Dravinja", "NK Krsko": "NK Krško",
    "NK Fuzinar": "NK Fužinar", "ND Ilirija 1911": "NK Ilirija 1911", "NK Tabor Sezana": "NK Tabor Sežana",
    "ND Beltinci": "ND Beltinci", "NK Triglav Kranj": "NK Triglav Kranj", "ND Bilje": "ND Bilje",
    "NK Kety Emmi Bistrica": "NK Bistrica", "ND Slovan Ljubljana": "NK Slovan", "NK Rudar Velenje": "NK Rudar Velenje",
}
# clubs whose Wikipedia infobox leaves the kit colours blank
COLOUR_OVERRIDES = {
    "Leeds United F.C.": ("#FFFFFF", "#1D428A"), "RC Celta de Vigo": ("#8AC3EE", "#FFFFFF"),
    "Deportivo de A Coruña": ("#1B4F9C", "#FFFFFF"), "Elche CF": ("#FFFFFF", "#05642C"),
    "RCD Espanyol": ("#007FC8", "#FFFFFF"), "CA Osasuna": ("#D91A21", "#0A346F"),
    "NK Olimpija Ljubljana": ("#00853E", "#FFFFFF"), "NŠ Mura": ("#111111", "#FFFFFF"),
    "FC Koper": ("#FFD200", "#0047AB"),
}
POS_SHORT = {
    "Goalkeeper": "GK", "Centre-Back": "CB", "Left-Back": "LB", "Right-Back": "RB", "Defender": "CB",
    "Defensive Midfield": "DM", "Central Midfield": "CM", "Midfield": "CM", "Attacking Midfield": "AM",
    "Left Midfield": "LM", "Right Midfield": "RM", "Left Winger": "LW", "Right Winger": "RW",
    "Second Striker": "SS", "Centre-Forward": "ST", "Attack": "ST",
}


def page_file(pages, title):
    return os.path.join(pages, re.sub(r"[^\w.-]+", "_", title) + ".wiki")


def kit_colours(pages, title, name):
    hexes = {}
    path = page_file(pages, title)
    if os.path.exists(path):
        txt = open(path).read()
        for k in ("body1", "leftarm1", "shorts1", "socks1"):
            m = re.search(r"\|\s*%s\s*=\s*#?([0-9A-Fa-f]{6})" % k, txt)
            if m:
                hexes[k] = "#" + m.group(1).upper()
    if "body1" not in hexes:  # deterministic fallback palette
        h = int(hashlib.sha1(name.encode()).hexdigest()[:6], 16)
        hue = h % 360
        return {"primary": f"hsl({hue},60%,40%)", "secondary": "#FFFFFF", "source": "generated"}
    primary = hexes["body1"]
    secondary = next((hexes[k] for k in ("leftarm1", "shorts1", "socks1") if k in hexes and hexes[k] != primary), None)
    if secondary is None:
        secondary = "#111111" if primary in ("#FFFFFF", "#FFFFF0") else "#FFFFFF"
    return {"primary": primary, "secondary": secondary, "source": "wikipedia"}


def age_at(dob, fallback):
    if not dob:
        return fallback or 25
    d = datetime.date.fromisoformat(dob)
    return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))


def rate(p, league):
    """0-100 overall + DLS-style attribute list scaled to 0-100."""
    if not p.get("market_value_eur"):
        a = age_at(p.get("dob"), p.get("age"))
        jitter = int(hashlib.sha1(p["name"].encode()).hexdigest()[:4], 16) % 9 - 4
        base = LEAGUE_META[league]["base"] - abs(a - 27) * 0.55 + jitter
        p = dict(p, market_value_eur=max(50_000, 2.5e6 * (math.exp((base - 56) / 7) - 1)))
    ov = B.overall(p)
    attrs = [round(x / 10) for x in B.ratings(p)]
    return round(ov), attrs, p.get("market_value_eur")


def calibrate(out):
    """Map each league's estimated ratings onto the real EA FC rating spread for that league.

    Players keep their order within the league (from the market-value estimate); their
    overall takes the same percentile in FC's distribution (fc_league_percentiles.json).
    Attributes move by the same amount. Leagues without FC data are left unchanged.
    """
    pct_path = os.path.join(HERE, "fc_league_percentiles.json")
    if not os.path.exists(pct_path):
        return
    fc = json.load(open(pct_path))
    for lg in out["leagues"]:
        if lg["id"] not in fc:
            continue
        pct = fc[lg["id"]]["pct"]
        ps = [p for p in out["players"] if out["clubs"][p["club"]]["league"] == lg["id"]]
        ps.sort(key=lambda p: (p["ovr"], p["value"]))
        n = len(ps)
        for i, p in enumerate(ps):
            target = pct[round(i / max(1, n - 1) * 100)]
            delta = target - p["ovr"]
            p["ovr"] = min(93, target)
            p["attrs"] = [max(5, min(99, a + delta)) if (k < 10 or p["pos"] == "GK") else a for k, a in enumerate(p["attrs"])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", required=True)
    ap.add_argument("--wiki-pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    roster = json.load(open(a.roster))
    smap = json.load(open(os.path.join(HERE, "..", "db", "slot_map.json")))
    display = smap["display"]
    out = {"season": "2026/27", "startDate": "2026-08-15", "leagues": [], "clubs": {}, "players": []}
    pid = 0
    for lg in LEAGUE_ORDER:
        meta = LEAGUE_META[lg]
        clubs = roster["leagues"][lg]["clubs"]
        ids = []
        for cname, c in clubs.items():
            long, short, city, stadium = display[cname]
            ascii_name = unicodedata.normalize("NFKD", long).encode("ascii", "ignore").decode()
            cid = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
            if cid in out["clubs"]:
                cid += "-" + lg
            ids.append(cid)
            col = kit_colours(a.wiki_pages, WIKI_TITLE.get(cname, cname), cname)
            if cname in COLOUR_OVERRIDES:
                col = {"primary": COLOUR_OVERRIDES[cname][0], "secondary": COLOUR_OVERRIDES[cname][1], "source": "manual"}
            out["clubs"][cid] = {"name": long, "short": short, "city": city, "stadium": stadium,
                                 "league": lg, "colors": col, "rosterName": cname, "dlsSlot": smap[lg][cname]}
            for p in c["players"]:
                ov, attrs, mv = rate(p, lg)
                pos = p.get("position") or "Central Midfield"
                out["players"].append({
                    "id": pid, "club": cid, "name": p["name"], "pos": POS_SHORT.get(pos, "CM"), "position": pos,
                    "age": age_at(p.get("dob"), p.get("age")), "dob": p.get("dob"),
                    "nat": (p.get("nationality") or "").replace(" / ", "/").split("/")[0].strip(),
                    "nat2": ((p.get("nationality") or "").replace(" / ", "/").split("/") + [""])[1].strip(),
                    "shirt": int(p["shirt"]) if str(p.get("shirt") or "").isdigit() else None,
                    "foot": p.get("foot"), "height": p.get("height_cm"),
                    "value": int(mv or 0), "contract": p.get("contract_expiry"),
                    "ovr": ov, "attrs": attrs,
                })
                pid += 1
        out["leagues"].append({"id": lg, "name": meta["name"], "country": meta["country"], "short": meta["short"],
                               "cycles": meta["cycles"], "clubs": ids})
    calibrate(out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out['clubs'])} clubs, {len(out['players'])} players -> {a.out} ({os.path.getsize(a.out)//1024} KB)")
    gen = [c["name"] for c in out["clubs"].values() if c["colors"]["source"] == "generated"]
    print("generated colours for:", gen)


if __name__ == "__main__":
    main()
