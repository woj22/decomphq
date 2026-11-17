#!/usr/bin/env python3
"""Work out DLS19's nationality ids by matching its players to Transfermarkt citizenship.

For every DLS19 player whose name (and birth year, when known) matches one Transfermarkt
player, record (DLS nationality id, TM country of citizenship). Each nationality id then
takes its most common country. Output: tools/db/nationality_ids.json  {country: id}.

Usage: python3 -I derive_nationalities.py <players.dat> <tm players.csv.gz> [out.json]
"""
import collections
import csv
import gzip
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dls_db as D  # noqa: E402


def fold(t):
    return " ".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().replace("-", " ").split())


def main():
    pl = D.Players(D.load(sys.argv[1]))
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "nationality_ids.json")
    tm = collections.defaultdict(list)
    for r in csv.DictReader(gzip.open(sys.argv[2], "rt", encoding="utf-8")):
        if r["country_of_citizenship"]:
            tm[fold(r["name"])].append(r)

    votes = collections.defaultdict(collections.Counter)
    for rec in pl.recs:
        p = pl.get(rec)
        cands = tm.get(fold(f"{p['first_name']} {p['surname']}"), [])
        if p["birth_year"] != 1900:
            cands = [c for c in cands if c["date_of_birth"][:4] == str(p["birth_year"])]
        if len(cands) == 1:
            votes[p["nationality"]][cands[0]["country_of_citizenship"]] += 1

    mapping, report = {}, []
    for nid, c in sorted(votes.items()):
        country, n = c.most_common(1)[0]
        total = sum(c.values())
        if n >= 2 and n / total >= 0.6:  # need a clear majority
            if country not in mapping or votes[mapping[country]][country] < n:
                mapping[country] = nid
        report.append((nid, country, n, total))
    json.dump(dict(sorted(mapping.items())), open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(mapping)} countries mapped from {sum(t for *_, t in report)} matched players -> {out}")
    weak = [r for r in report if r[2] < 2 or r[2] / r[3] < 0.6]
    if weak:
        print("ids without a clear country:", weak[:15])


if __name__ == "__main__":
    main()
