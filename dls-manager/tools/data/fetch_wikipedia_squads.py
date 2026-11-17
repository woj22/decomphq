#!/usr/bin/env python3
"""Fetch 2026/27 club lists and current squads from English Wikipedia.

Step 1: league season pages -> list of club article titles.
Step 2: each club article (and its "Template:<club> squad" if the article transcludes one)
        -> wikitext, cached in <out>/pages/.
Step 3: parse {{Fs player|no=|pos=|nat=|name=}} rows into <out>/squads.json.

Uses the MediaWiki API with a descriptive User-Agent, batches titles, and backs off on
HTTP 429. Cached pages are reused, so the script can be re-run after an interruption.

Usage: python3 -I fetch_wikipedia_squads.py --out <dir>
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
UA = "DLSManagerSquadTool/0.1 (personal non-commercial project; low request rate)"
LEAGUES = {
    "premier_league": "2026–27 Premier League",
    "la_liga": "2026–27 La Liga",
    "prvaliga": "2026–27 Slovenian PrvaLiga",
}


def api(params, tries=8):
    params = dict(params, format="json", formatversion=2)
    url = API + "?" + urllib.parse.urlencode(params)
    delay = 15
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = int(e.headers.get("Retry-After") or delay)
            print(f"  429, waiting {wait}s", flush=True)
            time.sleep(wait)
            delay = min(delay * 2, 300)
    raise RuntimeError("gave up after repeated 429s")


def fetch_pages(titles, cache):
    os.makedirs(cache, exist_ok=True)
    fname = lambda t: os.path.join(cache, re.sub(r"[^\w.-]+", "_", t) + ".wiki")
    todo = [t for t in titles if not os.path.exists(fname(t))]
    for k in range(0, len(todo), 5):
        batch = todo[k:k + 5]
        r = api({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                 "redirects": 1, "titles": "|".join(batch)})
        q = r["query"]
        alias = {}
        for x in q.get("normalized", []) + q.get("redirects", []):
            alias[x["to"]] = alias.get(x["from"], x["from"])
        for p in q["pages"]:
            text = p["revisions"][0]["slots"]["main"]["content"] if "revisions" in p else ""
            for t in {p["title"], alias.get(p["title"], p["title"])}:
                open(fname(t), "w").write(text)
        for t in batch:  # make sure every requested title gets a cache file
            if not os.path.exists(fname(t)):
                open(fname(t), "w").write("")
        print(f"  fetched {min(k + 5, len(todo))}/{len(todo)}", flush=True)
        time.sleep(6)
    return {t: open(fname(t)).read() for t in titles}


def league_clubs(text):
    anchor = text.find("Stadiums and locations")
    if anchor < 0:
        anchor = text.find("Teams")
    i = text.find("{|", anchor)
    table = text[i:text.find("|}", i)]
    clubs = []
    for row in table.split("|-")[1:]:
        m = re.search(r"\[\[([^\]|#]+)", row)
        if m:
            clubs.append(m.group(1).strip())
    return clubs


FS = re.compile(r"\{\{\s*(?:[Ff]s player|[Ff]ootball squad player)\s*\|(.*?)\}\}", re.S)


def parse_squad(text):
    """Return first-team rows from {{Fs player}} templates in the 'current squad' section."""
    sec = re.search(r"==+\s*(?:Current squad|First[- ]team squad|Players|Squad)\s*==+(.*?)(?:\n==[^=]|\Z)", text, re.S | re.I)
    body = sec.group(1) if sec else text
    # stop at "Out on loan" / "Other players" sub-sections
    body = re.split(r"===+\s*(?:Out on loan|Players out on loan|On loan)", body, flags=re.I)[0]
    rows = []
    for m in FS.finditer(body):
        f = {}
        for part in re.split(r"\|(?![^\[]*\]\])", m.group(1)):
            if "=" in part:
                k, v = part.split("=", 1)
                f[k.strip().lower()] = v.strip()
        name = f.get("name", "")
        link = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", name)
        disp = (link.group(2) or link.group(1)) if link else name
        disp = re.sub(r"\{\{.*?\}\}|<.*?>|'''?", "", disp).strip()
        if not disp:
            continue
        rows.append({"no": f.get("no", ""), "pos": f.get("pos", ""), "nat": f.get("nat", ""),
                     "name": disp, "article": link.group(1) if link else ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cache = os.path.join(a.out, "pages")

    print("league pages...", flush=True)
    lp = fetch_pages(list(LEAGUES.values()), cache)
    leagues = {k: league_clubs(lp[v]) for k, v in LEAGUES.items()}
    for k, v in leagues.items():
        print(f"{k}: {len(v)} clubs", flush=True)

    clubs = [c for v in leagues.values() for c in v]
    print("club pages...", flush=True)
    cp = fetch_pages(clubs, cache)

    # clubs whose squad lives in a separate template
    tpl_for = {}
    for c in clubs:
        if not FS.search(cp[c]):
            m = re.search(r"\{\{\s*([^{}|]*?squad[^{}|]*?)\s*\}\}", cp[c], re.I)
            if m:
                tpl_for[c] = "Template:" + m.group(1).strip()
    if tpl_for:
        print("squad templates...", flush=True)
        tp = fetch_pages(list(tpl_for.values()), cache)

    result = {}
    for lg, cl in leagues.items():
        result[lg] = {}
        for c in cl:
            text = tp[tpl_for[c]] if c in tpl_for else cp[c]
            result[lg][c] = parse_squad(text)
    json.dump(result, open(os.path.join(a.out, "squads.json"), "w"), ensure_ascii=False, indent=1)
    for lg, cl in result.items():
        for c, rows in cl.items():
            print(f"{lg:15s} {c:32s} {len(rows):3d} players", flush=True)


if __name__ == "__main__":
    main()
