#!/usr/bin/env python3
"""Download the open transfermarkt-datasets export and extract the leagues we use.

Source: https://github.com/dcaribou/transfermarkt-datasets (data published as
open files). We do NOT scrape transfermarkt.com directly.

Writes data/<LEAGUE>_clubs.csv and data/<LEAGUE>_players.csv for the most
recent season present in the export.

Usage: python3 -I fetch_transfermarkt.py --out ../../data [--leagues GB1 ES1]
"""
import argparse
import csv
import gzip
import io
import os
import urllib.request

BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
DEFAULT_LEAGUES = ["GB1", "ES1"]  # Premier League, LaLiga. Slovenia (SL1) is not in the export.


def fetch(name):
    req = urllib.request.Request(BASE + name + ".csv.gz", headers={"User-Agent": "curl/8.5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return list(csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(r.read())), "utf-8")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--leagues", nargs="*", default=DEFAULT_LEAGUES)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    clubs, players = fetch("clubs"), fetch("players")
    season = max(c["last_season"] for c in clubs)
    print("latest season in export:", season)
    for lg in a.leagues:
        cl = [c for c in clubs if c["domestic_competition_id"] == lg and c["last_season"] == season]
        ids = {c["club_id"] for c in cl}
        ps = [p for p in players if p["current_club_id"] in ids and p["last_season"] == season]
        for kind, rows in (("clubs", cl), ("players", ps)):
            path = os.path.join(a.out, f"{lg}_{kind}.csv")
            with open(path, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
                w.writeheader()
                w.writerows(rows)
        print(f"{lg}: {len(cl)} clubs, {len(ps)} players")


if __name__ == "__main__":
    main()
