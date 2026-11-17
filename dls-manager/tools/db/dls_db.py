#!/usr/bin/env python3
"""Read and write Dream League Soccer 2019 (v6.15) database files.

Files (inside the APK):
  assets/data/db/players.dat            players (v8, 180-byte records)
  assets/data/db/teamplayerlinks_0.dat  squads (264-byte team blocks)
  assets/data/db/teams.dat              teams (v9, 4,092-byte records; partly mapped)
  assets/data/text/ftsteamnames.xlc     team names (FTTL text bank, 13 languages)

The .dat files are single zlib streams; the .xlc file is not compressed.
See docs/formats/*.md for the layouts.

CLI:
  python3 -I dls_db.py dump-players <players.dat> [--csv out.csv] [--limit N]
  python3 -I dls_db.py dump-team <db_dir> <team_id>
"""
import argparse
import csv
import os
import struct
import sys
import zlib

# ---------------------------------------------------------------- helpers


def load(path):
    raw = open(path, "rb").read()
    return zlib.decompress(raw) if raw[:2] in (b"\x78\x9c", b"\x78\xda", b"\x78\x01") else raw


def save_zlib(path, data):
    open(path, "wb").write(zlib.compress(bytes(data), 9))


def put_utf16(buf, off, nchars, text):
    """Write a fixed-size, zero-padded UTF-16LE field (truncates to nchars-1 chars)."""
    enc = text[: nchars - 1].encode("utf-16le")
    buf[off:off + nchars * 2] = enc + b"\0" * (nchars * 2 - len(enc))


def get_utf16(buf, off, nchars):
    return bytes(buf[off:off + nchars * 2]).decode("utf-16le").split("\0")[0]


# ---------------------------------------------------------------- players

PLAYER_REC = 180
ATTR_NAMES = ["speed", "acceleration", "stamina", "strength", "tackling", "control",
              "shooting", "passing_a", "passing_b", "heading",
              "gk_1", "gk_2", "gk_3"]
# u16 fields: name -> offset
P16 = {
    "id": 0x00, "nationality": 0x6E, "unk_70": 0x70, "unk_72": 0x72, "unk_74": 0x74,
    "unk_76": 0x76, "height_cm": 0x78, "weight_kg": 0x7A, "pos_primary": 0x7C,
    "pos_secondary": 0x7E, "unk_80": 0x80, "unk_82": 0x82, "foot": 0x84,
    "unk_a0": 0xA0, "unk_a2": 0xA2, "unk_a4": 0xA4, "unk_a6": 0xA6,
    "birth_day": 0xA8, "birth_month": 0xAC, "birth_year": 0xB0,
}
FOOT = {"left": 0, "right": 1, "both": 3}  # 3 seen for Ronaldo, Kroos


class Players:
    def __init__(self, data):
        self.magic, self.version, count = struct.unpack_from("<III", data, 0)
        if self.version != 8 or 12 + PLAYER_REC * count != len(data):
            raise ValueError("unsupported players.dat layout")
        self.recs = [bytearray(data[12 + PLAYER_REC * i: 12 + PLAYER_REC * (i + 1)]) for i in range(count)]
        self.by_id = {struct.unpack_from("<H", r, 0)[0]: r for r in self.recs}

    def get(self, rec):
        p = {k: struct.unpack_from("<H", rec, o)[0] for k, o in P16.items()}
        p["first_name"] = get_utf16(rec, 0x02, 17)
        p["surname"] = get_utf16(rec, 0x24, 37)
        p["attr"] = list(struct.unpack_from("<13H", rec, 0x86))
        return p

    def set(self, rec, **kw):
        for k, v in kw.items():
            if k == "first_name":
                put_utf16(rec, 0x02, 17, v)
            elif k == "surname":
                put_utf16(rec, 0x24, 37, v)
            elif k == "attr":
                struct.pack_into("<13H", rec, 0x86, *[max(0, min(1000, int(a))) for a in v])
            else:
                struct.pack_into("<H", rec, P16[k], int(v) & 0xFFFF)

    def to_bytes(self):
        return struct.pack("<III", self.magic, self.version, len(self.recs)) + b"".join(self.recs)


def parse_players(data):  # kept for older scripts
    pl = Players(data)
    return {"magic": pl.magic, "version": pl.version, "players": [pl.get(r) for r in pl.recs]}


# ---------------------------------------------------------------- squads

LINK_BLOCK = 264
FLAG_STARTER, FLAG_CAPTAIN, FLAG_PEN, FLAG_FK, FLAG_CORNER_L, FLAG_CORNER_R = 1, 2, 4, 8, 0x10, 0x20


class Links:
    def __init__(self, data):
        self.header = data[:16]
        n = (len(data) - 16) // LINK_BLOCK
        if 16 + n * LINK_BLOCK != len(data):
            raise ValueError("unsupported teamplayerlinks layout")
        self.order, self.teams = [], {}
        for t in range(n):
            o = 16 + t * LINK_BLOCK
            tid, cnt = struct.unpack_from("<II", data, o)
            roles = [struct.unpack_from("<4B", data, o + 8 + 4 * i)[:3] for i in range(cnt)]
            ids = list(struct.unpack_from("<32I", data, o + 136)[:cnt])
            self.order.append(tid)
            self.teams[tid] = [{"shirt": s, "slot": sl, "flags": f, "player_id": pid}
                               for (s, sl, f), pid in zip(roles, ids)]

    def to_bytes(self):
        out = bytearray(self.header)
        for tid in self.order:
            sq = self.teams[tid]
            if len(sq) > 32:
                raise ValueError(f"team {tid}: more than 32 players")
            blk = bytearray(struct.pack("<II", tid, len(sq)))
            for i in range(32):
                blk += struct.pack("<4B", sq[i]["shirt"], sq[i]["slot"], sq[i]["flags"], 0) if i < len(sq) else b"\0" * 4
            for i in range(32):
                blk += struct.pack("<I", sq[i]["player_id"] if i < len(sq) else 0xFFFFFFFF)
            out += blk
        return bytes(out)


# ---------------------------------------------------------------- teams

TEAM_REC = 4092
SETPIECE_OFF = 0x114  # captain, free kick, left corner, penalty, right corner (player ids)


class Teams:
    def __init__(self, data):
        self.magic, self.version, count = struct.unpack_from("<III", data, 0)
        if 12 + TEAM_REC * count != len(data):
            raise ValueError("unsupported teams.dat layout")
        self.recs = [bytearray(data[12 + TEAM_REC * i: 12 + TEAM_REC * (i + 1)]) for i in range(count)]
        self.by_id = {struct.unpack_from("<I", r, 0)[0]: r for r in self.recs}

    def set_setpieces(self, tid, captain, free_kick, corner_l, penalty, corner_r):
        struct.pack_into("<5I", self.by_id[tid], SETPIECE_OFF, captain, free_kick, corner_l, penalty, corner_r)

    def stadium(self, tid):
        return get_utf16(self.by_id[tid], 0x140, 24)

    def set_stadium(self, tid, name):
        put_utf16(self.by_id[tid], 0x140, 24, name)

    def to_bytes(self):
        return struct.pack("<III", self.magic, self.version, len(self.recs)) + b"".join(self.recs)


# ---------------------------------------------------------------- text banks


class TextBank:
    """FTTL text bank: a key block plus one block of strings per language."""

    KEY_BLOCK_ID = 6

    def __init__(self, data):
        if data[:4] != b"FTTL":
            raise ValueError("not an FTTL text bank")
        self.pre = data[4:12]
        nb, nk, total = struct.unpack_from("<III", data, 0x0C)
        if total != len(data):
            raise ValueError("FTTL size mismatch")
        blocks = [struct.unpack_from("<II", data, 0x18 + 8 * i) for i in range(nb)]
        p = 0x18 + 8 * nb
        self.block_order, self.blocks = [], {}
        for size, bid in blocks:
            buf, out, q = data[p:p + size], [], 0
            for _ in range(nk):
                e = q
                while buf[e:e + 2] != b"\0\0":
                    e += 2
                out.append(buf[q:e].decode("utf-16le"))
                q = e + 2
            self.block_order.append(bid)
            self.blocks[bid] = out
            p += size
        self.keys = self.blocks[self.KEY_BLOCK_ID]
        self.index = {k: i for i, k in enumerate(self.keys)}

    def get(self, key, lang=0):
        return self.blocks[lang][self.index[key]]

    def set(self, key, value, langs=None):
        i = self.index[key]
        for bid in self.block_order:
            if bid != self.KEY_BLOCK_ID and (langs is None or bid in langs):
                self.blocks[bid][i] = value

    def to_bytes(self):
        bodies = [b"".join(s.encode("utf-16le") + b"\0\0" for s in self.blocks[bid]) for bid in self.block_order]
        head_len = 0x18 + 8 * len(self.block_order)
        total = head_len + sum(len(b) for b in bodies)
        out = bytearray(b"FTTL" + self.pre + struct.pack("<III", len(self.block_order), len(self.keys), total))
        for bid, body in zip(self.block_order, bodies):
            out += struct.pack("<II", len(body), bid)
        for body in bodies:
            out += body
        return bytes(out)


NATIONAL_TEAM_BASE = 199  # nationality id n <-> national team id 199 + n


def nationality_table(names, derived_path=None):
    """Country name -> DLS19 nationality id.

    Ids 0-39 follow the national-team slots (team 199 + id), verified against squads.
    Higher ids drift from that order, so they come from nationality_ids.json, which
    derive_nationalities.py builds by matching DLS19 players to Transfermarkt citizenship.
    Country names use Transfermarkt spelling ("Korea, South", "Cote d'Ivoire", ...).
    """
    derived_path = derived_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "nationality_ids.json")
    out = {}
    if os.path.exists(derived_path):
        import json
        out.update(json.load(open(derived_path)))
    verified = {}
    for n in range(40):
        key = f"TXT_TEAMNAMELONG_{NATIONAL_TEAM_BASE + n}"
        if key in names.index:
            verified[names.get(key)] = n
    # DLS name -> Transfermarkt spelling for the verified block
    alias = {"USA": "United States", "Korea Republic": "Korea, South", "Republic of Ireland": "Ireland",
             "Côte d'Ivoire": "Cote d'Ivoire", "Turkey": "Türkiye"}
    for name, n in verified.items():
        out = {k: v for k, v in out.items() if v != n}  # the verified owner of this id wins
        out[alias.get(name, name)] = n
    return out


NAT_ALIASES = {"Korea South": "Korea, South", "Turkey": "Türkiye", "Ivory Coast": "Cote d'Ivoire",
               "Côte d'Ivoire": "Cote d'Ivoire", "USA": "United States", "Bosnia and Herzegovina": "Bosnia-Herzegovina",
               "Republic of Ireland": "Ireland", "Gambia": "The Gambia", "Congo DR": "DR Congo"}


def nationality_id(table, text):
    """'England / Jamaica' -> first nationality DLS19 knows, else None."""
    for part in (text or "").replace("/", " / ").split(" / "):
        part = NAT_ALIASES.get(part.strip(), part.strip())
        if part in table:
            return table[part]
    return None


# ---------------------------------------------------------------- CLI


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump-players")
    d.add_argument("path")
    d.add_argument("--csv")
    d.add_argument("--limit", type=int, default=20)
    t = sub.add_parser("dump-team")
    t.add_argument("db_dir", help="folder with players.dat, teamplayerlinks_0.dat, teams.dat, ftsteamnames.xlc")
    t.add_argument("team_id", type=int)
    a = ap.parse_args()

    if a.cmd == "dump-players":
        pl = Players(load(a.path))
        rows = [pl.get(r) for r in pl.recs]
        print(f"version {pl.version}, {len(rows)} players", file=sys.stderr)
        if a.csv:
            with open(a.csv, "w", newline="") as fh:
                w = csv.writer(fh)
                keys = ["id", "first_name", "surname"] + [k for k in P16 if k != "id"]
                w.writerow(keys + ATTR_NAMES)
                for p in rows:
                    w.writerow([p[k] for k in keys] + p["attr"])
        for p in rows[: a.limit]:
            print(p["id"], p["first_name"], p["surname"], p["height_cm"], p["attr"])
    else:
        dd = a.db_dir
        pl = Players(load(os.path.join(dd, "players.dat")))
        ln = Links(load(os.path.join(dd, "teamplayerlinks_0.dat")))
        tm = Teams(load(os.path.join(dd, "teams.dat")))
        nm = TextBank(load(os.path.join(dd, "ftsteamnames.xlc")))
        tid = a.team_id
        print(nm.get(f"TXT_TEAMNAMELONG_{tid}"), "|", nm.get(f"TXT_TEAMNAMESHORT_{tid}"), "|", tm.stadium(tid))
        print("set pieces:", struct.unpack_from("<5I", tm.by_id[tid], SETPIECE_OFF))
        for e in ln.teams[tid]:
            p = pl.get(pl.by_id[e["player_id"]])
            print(f"  #{e['shirt']:>2} slot {e['slot']:>2} flags {e['flags']:#04x}  {p['first_name']} {p['surname']}"
                  f"  nat {p['nationality']}  {p['attr'][:10]}")


if __name__ == "__main__":
    main()
