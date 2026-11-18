#!/usr/bin/env python3
"""Give every player who has DLS's generic head a look of his own.

DLS19's appearance fields in players.dat (worked out from players whose looks are known in
the original database):
    unk_76  skin tone      0 lightest .. 4 darkest, 5 East Asian
    unk_70  hair colour    0 black, 1 dark blond / light brown, 2 brown, 5 blond
    unk_74  facial hair    0 none, 2-3 stubble, 4 short beard, 5 goatee, 7 full beard
    unk_72  hair style     e.g. 1 close crop, 2 short side part, 14 short textured, 44/49 medium,
                           22 long, 21 big curls, 17/51/18 short or shaved (black hair),
                           8 short afro, 37 short with a line, 10 East Asian
Players who were already in DLS19 (their own record) and players with a real face scan keep
theirs. For the rest the look comes from the nationality (photo reading was tried and dropped: lighting
made it unreliable); the hair style is chosen to suit.
Each choice is seeded by the player, so rebuilding gives the same faces.

Usage: python3 -I set_heads.py --db <built db dir> --orig <original players.dat>
           --clubs clubs.json --data menu/data.json --faces face_ids.json --headshots assets/headshots
"""
import argparse
import hashlib
import json
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dls_db as D  # noqa: E402

LIGHT = {"Slovenia", "Croatia", "Serbia", "Bosnia-Herzegovina", "Montenegro", "North Macedonia", "N. Macedonia", "Kosovo",
         "Poland", "Czech Republic", "Slovakia", "Hungary", "Ukraine", "Russia", "Romania", "Bulgaria", "Lithuania", "Estonia",
         "Iceland", "Finland", "Faroe Islands", "Scotland", "Ireland", "Northern Ireland", "Wales", "Austria", "Georgia", "Azerbaijan", "Uzbekistan"}
NORDIC = {"Sweden", "Norway", "Denmark", "Iceland", "Finland", "Faroe Islands", "Netherlands", "Germany", "Estonia", "Lithuania"}
WEST = {"England": [.3, .35, .1, .15, .1], "France": [.15, .3, .15, .2, .2], "Belgium": [.25, .35, .1, .15, .15],
        "Netherlands": [.25, .35, .1, .15, .15], "Germany": [.3, .4, .15, .1, .05], "Sweden": [.4, .35, .1, .08, .07],
        "Norway": [.45, .35, .1, .05, .05], "Denmark": [.45, .35, .1, .05, .05], "Switzerland": [.35, .35, .15, .08, .07],
        "Canada": [.25, .35, .15, .15, .1], "United States": [.25, .35, .15, .15, .1], "USA": [.25, .35, .15, .15, .1],
        "Australia": [.35, .4, .15, .05, .05], "New Zealand": [.35, .4, .15, .05, .05], "Italy": [.1, .45, .4, .03, .02],
        "Portugal": [.05, .35, .45, .1, .05], "Spain": [.08, .42, .45, .03, .02], "Greece": [.05, .4, .55, 0, 0],
        "Türkiye": [0, .3, .7, 0, 0], "Albania": [.05, .45, .5, 0, 0], "Israel": [.1, .4, .5, 0, 0]}
LATIN = {"Argentina": [0, .45, .5, .05, 0], "Uruguay": [0, .45, .45, .1, 0], "Chile": [0, .3, .65, .05, 0],
         "Brazil": [0, .25, .35, .25, .15], "Colombia": [0, .15, .55, .2, .1], "Ecuador": [0, 0, .4, .3, .3],
         "Venezuela": [0, .2, .55, .2, .05], "Paraguay": [0, .2, .75, .05, 0], "Mexico": [0, .2, .75, .05, 0],
         "Dominican Republic": [0, 0, .3, .5, .2], "Dominican Rep.": [0, 0, .3, .5, .2], "Guadeloupe": [0, 0, .1, .5, .4],
         "Haiti": [0, 0, 0, .3, .7], "Jamaica": [0, 0, 0, .4, .6]}
AFRICA = {"Nigeria", "Senegal", "Cote d'Ivoire", "Ghana", "Cameroon", "DR Congo", "The Gambia", "Mali", "Guinea", "Togo",
          "Burkina Faso", "Mozambique", "Guinea-Bissau", "Gabon", "Angola", "Kenya", "Cape Verde", "Congo", "Madagascar",
          "Sierra Leone", "Uganda", "Mauritania"}
NORTH_AFRICA = {"Morocco", "Algeria", "Tunisia", "Egypt"}
EAST_ASIA = {"Japan", "Korea South", "Korea, South", "China", "Indonesia", "Malaysia"}


def skin_dist(nat):
    if nat in EAST_ASIA:
        return [0, 0, 0, 0, 0, 1]
    if nat in WEST:
        return WEST[nat] + [0]
    if nat in LATIN:
        return LATIN[nat] + [0]
    if nat in AFRICA:
        return [0, 0, 0, .4, .6, 0]
    if nat in NORTH_AFRICA:
        return [0, .1, .75, .15, 0, 0]
    if nat in LIGHT:
        return [.45, .45, .08, .02, 0, 0]
    if nat == "India":
        return [0, 0, .7, .3, 0, 0]
    return [.2, .35, .3, .1, .05, 0]


def pick(r, dist):
    x = r.random() * sum(dist)
    for i, w in enumerate(dist):
        x -= w
        if x <= 0:
            return i
    return len(dist) - 1


def wpick(r, opts):
    return opts[pick(r, [w for _, w in opts])][0]


def photo_look(path):
    """Skin tone, hair colour, beard and whether the head looks shaved, from a 96px face crop."""
    img = cv2.imread(path)
    if img is None:
        return None
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    cheeks = np.concatenate([lab[44:56, 30:40].reshape(-1, 3), lab[44:56, 56:66].reshape(-1, 3)])
    L, A, B = np.median(cheeks, axis=0)
    chin = np.median(lab[62:70, 40:56].reshape(-1, 3), axis=0)
    top = np.median(lab[8:17, 36:60].reshape(-1, 3), axis=0)
    bg = np.median(np.concatenate([lab[0:6, 0:10].reshape(-1, 3), lab[0:6, 86:96].reshape(-1, 3)]), axis=0)
    skin = 0 if L > 182 else 1 if L > 160 else 2 if L > 138 else 3 if L > 108 else 4
    beard_d = L - chin[0]
    beard = 7 if beard_d > 38 else 4 if beard_d > 24 else 3 if beard_d > 14 else 0
    # the hair: what's on top of the head, unless that's the background or skin (shaved / bald)
    hairL = top[0]
    bald = abs(top[0] - bg[0]) < 10 and abs(top[2] - bg[2]) < 6 or abs(top[0] - L) < 12
    hair = 0 if hairL < 70 else 2 if hairL < 110 else 1 if hairL < 150 else 5
    return {"skin": skin, "hair": hair, "beard": beard, "bald": bald}


def style_for(r, skin, bald, nat):
    if skin == 5:
        return 10
    if skin >= 3:
        return wpick(r, [(51, .3), (18, .1), (8, .25), (37, .1), (9, .1), (5, .05)]) if bald else \
            wpick(r, [(17, .3), (8, .25), (37, .15), (9, .1), (5, .08), (21, .07), (15, .05)])
    if bald:
        return wpick(r, [(1, .7), (15, .3)])
    return wpick(r, [(1, .2), (2, .14), (14, .16), (42, .1), (44, .14), (49, .1), (45, .06), (46, .05), (22, .03), (21, .02)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--orig", required=True)
    ap.add_argument("--clubs", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--faces", required=True)
    ap.add_argument("--headshots", required=True)
    a = ap.parse_args()
    faces = set(json.load(open(a.faces)))
    orig = D.Players(D.load(a.orig))
    pl = D.Players(D.load(os.path.join(a.db, "players.dat")))
    clubs = json.load(open(a.clubs, encoding="utf-8"))
    data = json.load(open(a.data, encoding="utf-8"))
    by_name = {}
    for p in data["players"]:
        by_name.setdefault((p["club"], p["name"].lower()), p)
    kept = photo = nat = 0
    for cid, c in clubs.items():
        for x in c["players"]:
            pid = x["id"]
            if pid not in pl.by_id:
                continue
            o = orig.get(orig.by_id[pid]) if pid in orig.by_id else None
            own = o is not None and o["surname"].lower() == x["sn"].lower() and o["birth_year"] in (x["by"], x["by"] - 1, x["by"] + 1, 1900)
            if own or pid in faces:
                kept += 1
                continue
            p = by_name.get((cid, (x["fn"] + " " + x["sn"]).strip().lower())) or by_name.get((cid, x["sn"].lower()))
            natn = p["nat"] if p else ""
            r = random.Random(int(hashlib.sha1(f"{pid}:{x['fn']}{x['sn']}".encode()).hexdigest()[:8], 16))
            look = None
            if natn in EAST_ASIA:
                skin = 5
            elif look:
                skin = look["skin"]
            else:
                skin = pick(r, skin_dist(natn))
            if look:
                hair = 0 if skin >= 3 or skin == 5 else look["hair"]
                beard = look["beard"]
                bald = look["bald"]
                photo += 1
            else:
                if skin >= 2:
                    hair = 0 if skin >= 3 or r.random() < .75 else 2
                else:
                    hair = wpick(r, [(2, .4), (0, .22), (1, .22), (5, .16)] if natn in NORDIC else [(2, .45), (0, .3), (1, .17), (5, .08)])
                age = (p or {}).get("age") or 25
                beard = wpick(r, [(0, .5 if age < 24 else .35), (2, .14), (3, .12), (4, .14), (7, .1 if age < 24 else .2), (5, .04)])
                bald = r.random() < (0.06 if age < 28 else 0.15)
                nat += 1
            style = style_for(r, skin, bald, natn)
            pl.set(pl.by_id[pid], unk_76=skin, unk_70=hair, unk_74=beard, unk_72=style)
    D.save_zlib(os.path.join(a.db, "players.dat"), pl.to_bytes())
    print(f"kept their own DLS look: {kept}; set from a photo: {photo}; set from nationality: {nat}")


if __name__ == "__main__":
    main()
