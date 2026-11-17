#!/usr/bin/env python3
"""Write every club from menu/data.json into the DLS19 database in one pass.

Same source as the manager menus (ratings, positions, shirts, nationalities), so the
game and the menus agree. Each club goes into the slot named in slot_map.json.

Player records:
  * a player already in DLS19 (same name, compatible birth year) keeps his own record,
    and so his face/hair;
  * everyone else overwrites, in order: records of the replaced slots' old squads,
    records linked to no team, then records only used by national teams.
Old links to overwritten records are removed from teams we do not replace.

Usage:
  python3 -I build_all.py --db <dir with original players.dat, teamplayerlinks_0.dat,
      teams.dat, ftsteamnames.xlc> --data menu/data.json --out <dir> [--badges assets/badges]
Writes the four DB files plus teams/t<slot>.png and t<slot>_thumb.png when badges exist,
and slots.json (club id -> slot id) for the APK step and the menus.
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dls_db as D  # noqa: E402
import build_team as B  # noqa: E402

GENERIC_HEAD = {"unk_70": 0, "unk_72": 1, "unk_74": 0}
# clubs whose slot_map entry is their own DLS19 team (keep its kits)
OWN_SLOT = {"Manchester City F.C.", "Manchester United F.C.", "Tottenham Hotspur F.C.", "Aston Villa F.C.",
            "Nottingham Forest F.C.", "Atlético Madrid", "Athletic Bilbao", "Deportivo de A Coruña",
            "RCD Espanyol", "Real Madrid CF", "Real Sociedad", "Sevilla FC", "RC Celta de Vigo",
            "Rayo Vallecano", "Real Betis", "Deportivo Alavés"}


def fold(t):
    return " ".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().split())


def fix_xi(squad, rec_ovr):
    """Exactly 11 starters with one goalkeeper (in slot 0) and a captain."""
    starters = [e for e in squad if e["flags"] & D.FLAG_STARTER]
    gks = [e for e in starters if e["slot"] == 0]
    if len(starters) == 11 and len(gks) == 1 and any(e["flags"] & D.FLAG_CAPTAIN for e in squad):
        return
    for e in squad:
        e["flags"] &= ~(D.FLAG_STARTER | D.FLAG_CAPTAIN)
    best = lambda e: -rec_ovr.get(e["player_id"], 0)
    gk = sorted([e for e in squad if e["slot"] == 0], key=best)[:1]
    rest = sorted([e for e in squad if e not in gk and e["slot"] != 0], key=best)[: 11 - len(gk)]
    for e in gk + rest:
        e["flags"] |= D.FLAG_STARTER
    if rest:
        rest[0]["flags"] |= D.FLAG_CAPTAIN
    squad.sort(key=lambda e: not e["flags"] & D.FLAG_STARTER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--badges")
    ap.add_argument("--kits", help="kits json (club id -> home/away/third); applied to borrowed slots only")
    ap.add_argument("--existing-badges", help="folder of the APK's own teams/*.png; other teams get a generated badge")
    a = ap.parse_args()

    pl = D.Players(D.load(os.path.join(a.db, "players.dat")))
    ln = D.Links(D.load(os.path.join(a.db, "teamplayerlinks_0.dat")))
    tm = D.Teams(D.load(os.path.join(a.db, "teams.dat")))
    nm = D.TextBank(D.load(os.path.join(a.db, "ftsteamnames.xlc")))
    nat_ids = D.nationality_table(nm)
    data = json.load(open(a.data))
    smap = json.load(open(os.path.join(HERE, "slot_map.json")))

    # ---- club -> slot id
    name_to_slot = {}
    for t in ln.order:
        name_to_slot.setdefault(nm.get(f"TXT_TEAMNAMELONG_{t}"), t)
    slot_of = {}
    for cid, c in data["clubs"].items():
        want = smap[c["league"]][c["rosterName"]]
        if want not in name_to_slot or want == "":
            sys.exit(f"slot {want!r} for {c['name']} not found")
        slot_of[cid] = name_to_slot[want]
    if len(set(slot_of.values())) != len(slot_of):
        sys.exit("two clubs share a slot")
    replaced = set(slot_of.values())

    # ---- which DLS records can be reused / overwritten
    by_name = {}
    for pid, rec in pl.by_id.items():
        q = pl.get(rec)
        by_name.setdefault(fold(f"{q['first_name']} {q['surname']}"), []).append((pid, q))

    def existing(p):
        cands = by_name.get(fold(p["name"]), [])
        if p.get("dob"):
            y = int(p["dob"][:4])
            cands = [c for c in cands if c[1]["birth_year"] in (y - 1, y, y + 1, 1900)]
        return cands[0][0] if len(cands) == 1 else None

    players_by_club = {}
    for p in data["players"]:
        players_by_club.setdefault(p["club"], []).append(p)

    target = {}  # roster player id -> DLS record id
    for p in data["players"]:
        pid = existing(p)
        if pid is not None and pid not in target.values():
            target[p["id"]] = pid
    reused = set(target.values())

    linked_to = {}
    for tid, sq in ln.teams.items():
        for e in sq:
            linked_to.setdefault(e["player_id"], set()).add(tid)
    # national team = original squad is (almost) all one nationality, at slot 199 + that nationality
    national = set()
    for t in ln.order:
        nats = [pl.get(pl.by_id[e["player_id"]])["nationality"] for e in ln.teams[t]]
        if nats and max(nats.count(n) for n in set(nats)) >= 0.9 * len(nats) and t >= D.NATIONAL_TEAM_BASE:
            national.add(t)
    pool = []
    pool += [e["player_id"] for t in ln.order if t in replaced for e in ln.teams[t]]
    pool += [x for x in pl.by_id if x not in linked_to]
    pool += [x for x, ts in linked_to.items() if ts and ts <= (national | replaced)]
    pool += [x for x in pl.by_id]  # last resort
    seen, ordered = set(), []
    for x in pool:
        if x not in seen and x not in reused:
            seen.add(x)
            ordered.append(x)
    it = iter(ordered)
    for p in data["players"]:
        if p["id"] not in target:
            target[p["id"]] = next(it)
    overwritten = {target[p["id"]] for p in data["players"]} - reused

    # ---- write player records
    unknown_nat = set()
    for p in data["players"]:
        rec = pl.by_id[target[p["id"]]]
        first, last = B.split_name(p["name"])
        nat = D.nationality_id(nat_ids, p["nat"] + ("/" + p["nat2"] if p.get("nat2") else ""))
        if nat is None:
            unknown_nat.add(p["nat"])
        dob = datetime.date.fromisoformat(p["dob"]) if p.get("dob") else None
        slot = B.POS.get(p["position"], ("CM", 9))[1]
        attrs = [x * 10 for x in p["attrs"]]
        fields = dict(first_name=first, surname=last, height_cm=p.get("height") or 180,
                      weight_kg=int(round((p.get("height") or 180) * 0.42)), foot=D.FOOT.get(p.get("foot") or "right", 1),
                      pos_primary=slot, pos_secondary=slot, attr=attrs,
                      birth_day=dob.day if dob else 1, birth_month=dob.month if dob else 1,
                      birth_year=dob.year if dob else 1900)
        if nat is not None:
            fields["nationality"] = nat
        if target[p["id"]] in overwritten:
            fields.update(GENERIC_HEAD)
        pl.set(rec, **fields)

    # ---- remove overwritten records from teams we keep
    for t in ln.order:
        if t not in replaced:
            ln.teams[t] = [e for e in ln.teams[t] if e["player_id"] not in overwritten]
    # national teams that lost players: refill from our 2026/27 players of that nationality,
    # other short teams: top up with old records nobody uses any more
    rec_ovr = {target[p["id"]]: p["ovr"] for p in data["players"]}
    rec_pos = {target[p["id"]]: B.POS.get(p["position"], ("CM", 9))[1] for p in data["players"]}
    by_nat = {}
    for p in data["players"]:
        n = pl.get(pl.by_id[target[p["id"]]])["nationality"]
        by_nat.setdefault(n, []).append(target[p["id"]])
    still_linked = {e["player_id"] for t in ln.order for e in ln.teams[t]} | set(target.values())
    spare_old = [x for x in pl.by_id if x not in still_linked]
    refilled = {}
    for t in ln.order:
        if t in replaced:
            continue
        pool_nat = by_nat.get(t - D.NATIONAL_TEAM_BASE, []) if t in national else []
        if t in national and len(pool_nat) >= 16:
            ln.teams[t] = []  # enough current players: pick the whole squad from 2026/27
        elif len(ln.teams[t]) >= 18 and any(e["slot"] == 0 for e in ln.teams[t]):
            continue
        have = {e["player_id"] for e in ln.teams[t]}
        if t in national:
            ranked = sorted((x for x in pool_nat if x not in have), key=lambda x: -rec_ovr[x])
            grp = lambda x: "GK" if rec_pos[x] == 0 else "DF" if rec_pos[x] in (1, 2, 5, 7) else "FW" if rec_pos[x] >= 19 else "MF"
            room = max(1, 23 - len(ln.teams[t]))
            quota = {"GK": 3, "DF": 8, "MF": 7, "FW": 5}
            have_g = {}
            for e in ln.teams[t]:
                g = "GK" if e["slot"] == 0 else "DF" if e["slot"] in (1, 2, 5, 7) else "FW" if e["slot"] >= 19 else "MF"
                have_g[g] = have_g.get(g, 0) + 1
            picked = []
            for g, q in quota.items():
                picked += [x for x in ranked if grp(x) == g][: max(0, q - have_g.get(g, 0))]
            picked += [x for x in ranked if x not in picked]
            cands = picked[:room]
            if not any(rec_pos.get(x) == 0 for x in cands) and not any(e["slot"] == 0 for e in ln.teams[t]):
                old_gk = next((x for x in spare_old if pl.get(pl.by_id[x])["pos_primary"] == 0), None)
                if old_gk is not None:  # no keeper of this nation in our leagues: borrow an unused one
                    spare_old.remove(old_gk)
                    pl.set(pl.by_id[old_gk], nationality=t - D.NATIONAL_TEAM_BASE)
                    rec_pos[old_gk] = 0
                    rec_ovr[old_gk] = pl.get(pl.by_id[old_gk])["attr"][10] // 10
                    cands = cands[:-1] + [old_gk] if len(cands) >= room else cands + [old_gk]
        else:
            cands = spare_old
        shirts = {e["shirt"] for e in ln.teams[t]}
        free = (n for n in range(1, 99) if n not in shirts)
        for x in cands:
            if len(ln.teams[t]) >= 23:
                break
            if x in have:
                continue
            slot = rec_pos.get(x, pl.get(pl.by_id[x])["pos_primary"])
            ln.teams[t].append({"shirt": next(free), "slot": slot, "flags": 0, "player_id": x})
            have.add(x)
            if t not in national:
                spare_old.remove(x)
        refilled[t] = len(ln.teams[t])
        fix_xi(ln.teams[t], rec_ovr)
    for t in ln.order:
        if t not in replaced:
            ln.teams[t] = ln.teams[t][:32]
            fix_xi(ln.teams[t], rec_ovr)
    thin = {t: len(ln.teams[t]) for t in ln.order if t not in replaced and len(ln.teams[t]) < 16}

    # ---- squads, names, stadiums, set pieces
    for cid, tid in slot_of.items():
        c = data["clubs"][cid]
        squad = sorted(players_by_club[cid], key=lambda p: -p["ovr"])[:32]
        used, xi = set(), {}
        for label, code in B.XI_SLOTS:
            cands = [p for p in squad if p["id"] not in used and p["position"] in B.SLOT_FITS[label]]
            if not cands:
                cands = [p for p in squad if p["id"] not in used and p["pos"] != "GK"]
            best = max(cands, key=lambda p: p["ovr"])
            used.add(best["id"])
            xi[best["id"]] = code
        starters = [p for p in squad if p["id"] in xi]
        outfield = [p for p in starters if p["pos"] != "GK"]
        captain = max(outfield, key=lambda p: (p["age"] >= 25, p["ovr"]))
        pen = max(outfield, key=lambda p: p["attrs"][6])
        fk = max(outfield, key=lambda p: p["attrs"][7] + p["attrs"][6])
        corner = max(outfield, key=lambda p: p["attrs"][7])
        taken = {p["shirt"] for p in squad if p.get("shirt")}
        free = (n for n in range(2, 99) if n not in taken)
        links = []
        order = [p for lab, code in B.XI_SLOTS for p in starters if xi[p["id"]] == code] + [p for p in squad if p["id"] not in xi]
        for p in order:
            shirt = p.get("shirt") or (1 if p["pos"] == "GK" and 1 not in taken else next(free))
            taken.add(shirt)
            flags = (D.FLAG_STARTER if p["id"] in xi else 0) | (D.FLAG_CAPTAIN if p is captain else 0) | \
                (D.FLAG_PEN if p is pen else 0) | (D.FLAG_FK if p is fk else 0) | \
                ((D.FLAG_CORNER_L | D.FLAG_CORNER_R) if p is corner else 0)
            links.append({"shirt": min(99, int(shirt)), "slot": xi.get(p["id"], B.POS.get(p["position"], ("CM", 9))[1]),
                          "flags": flags, "player_id": target[p["id"]]})
        ln.teams[tid] = links
        tm.set_setpieces(tid, target[captain["id"]], target[fk["id"]], target[corner["id"]], target[pen["id"]], target[corner["id"]])
        long, short, city, stadium = smap["display"][c["rosterName"]]
        nm.set(f"TXT_TEAMNAMELONG_{tid}", long)
        nm.set(f"TXT_TEAMNAMEMED_{tid}", long if len(long) <= 16 else c["name"][:16])
        nm.set(f"TXT_TEAMNAMESHORT_{tid}", short)
        nm.set(f"TXT_TEAMNAMECITY_{tid}", city)
        tm.set_stadium(tid, stadium)

    # ---- kits: clubs that kept their own DLS slot keep their kits; borrowed slots get real colours
    kits = json.load(open(a.kits)) if a.kits and os.path.exists(a.kits) else {}
    kits_done = []
    for cid, tid in slot_of.items():
        c = data["clubs"][cid]
        slot_words = [w for w in fold(smap[c["league"]][c["rosterName"]]).split() if len(w) >= 3]
        own_slot = c["rosterName"] in OWN_SLOT or any(w in fold(c["name"]).split() for w in slot_words)
        if own_slot or cid not in kits:
            continue
        for k, kit in enumerate(("home", "away", "third")):
            if kit in kits[cid]:
                v = kits[cid][kit]
                tm.set_kit(tid, k, v["shirt"], v.get("shirt2", v["shirt"]), v["shorts"], v["socks"], v.get("pattern", "plain"))
        kits_done.append(c["name"])

    # ---- write files
    os.makedirs(a.out, exist_ok=True)
    D.save_zlib(os.path.join(a.out, "players.dat"), pl.to_bytes())
    D.save_zlib(os.path.join(a.out, "teamplayerlinks_0.dat"), ln.to_bytes())
    D.save_zlib(os.path.join(a.out, "teams.dat"), tm.to_bytes())
    open(os.path.join(a.out, "ftsteamnames.xlc"), "wb").write(nm.to_bytes())
    badges = 0
    if a.badges:
        os.makedirs(os.path.join(a.out, "teams"), exist_ok=True)
        for cid, tid in slot_of.items():
            b256 = os.path.join(a.badges, "256", cid + ".png")
            b64 = os.path.join(a.badges, "64", cid + ".png")
            if os.path.exists(b256) and os.path.exists(b64):
                shutil.copy(b256, os.path.join(a.out, "teams", f"t{tid}.png"))
                shutil.copy(b64, os.path.join(a.out, "teams", f"t{tid}_thumb.png"))
                badges += 1
    generated = 0
    if a.existing_badges:
        from PIL import Image, ImageDraw, ImageFont
        have = set(os.listdir(os.path.join(a.out, "teams"))) if os.path.isdir(os.path.join(a.out, "teams")) else set()
        have |= set(os.listdir(a.existing_badges))
        os.makedirs(os.path.join(a.out, "teams"), exist_ok=True)
        font_path = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",) if os.path.exists(p)), None)
        for tid in ln.order:
            if f"t{tid}.png" in have:
                continue
            def sat(h):
                r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
                return max(r, g, b) - min(r, g, b)
            cols = [tm.kit_colour(tid, 0, i) for i in range(10)]
            primary = max(cols, key=sat) if max(sat(c) for c in cols) > 60 else cols[0]
            if primary in ("#FFFFFF",):
                primary = next((c for c in cols if c != "#FFFFFF"), "#14213D")
            lum = sum(int(primary[i:i + 2], 16) for i in (1, 3, 5)) / 3
            secondary = "#FFFFFF" if lum < 170 else "#14213D"
            short = nm.get(f"TXT_TEAMNAMESHORT_{tid}")[:3].upper()
            for size, suffix in ((256, ""), (64, "_thumb")):
                img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                s_ = size / 100
                shield = [(14 * s_, 8 * s_), (86 * s_, 8 * s_), (86 * s_, 50 * s_), (50 * s_, 94 * s_), (14 * s_, 50 * s_)]
                d.polygon(shield, fill=primary, outline=secondary, width=max(2, int(5 * s_)))
                d.polygon([(20 * s_, 14 * s_), (80 * s_, 14 * s_), (80 * s_, 49 * s_), (50 * s_, 86 * s_), (20 * s_, 49 * s_)],
                          outline=secondary, width=max(1, int(1.5 * s_)))
                if font_path:
                    fnt = ImageFont.truetype(font_path, int(22 * s_))
                    ink = secondary
                    d.text((50 * s_, 42 * s_), short, font=fnt, fill=ink, anchor="mm", stroke_width=max(1, int(s_)), stroke_fill=secondary)
                img.save(os.path.join(a.out, "teams", f"t{tid}{suffix}.png"), optimize=True)
            generated += 1
    json.dump({cid: tid for cid, tid in slot_of.items()}, open(os.path.join(a.out, "slots.json"), "w"), indent=1)
    print(f"kits written for {len(kits_done)} clubs in borrowed slots; generated badges for {generated} other teams")

    print(f"{len(slot_of)} clubs written; {len(data['players'])} players "
          f"({len(reused)} kept their own DLS19 record/face, {len(overwritten)} new); badges: {badges}")
    if unknown_nat:
        print("nationalities DLS19 lacks (kept previous):", sorted(unknown_nat))
    if refilled:
        print(f"refilled {len(refilled)} teams (national teams with 2026/27 players)")
    if thin:
        print("teams still under 16 players:", {nm.get(f'TXT_TEAMNAMELONG_{t}'): n for t, n in thin.items()})


if __name__ == "__main__":
    main()
