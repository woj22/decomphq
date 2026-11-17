#!/usr/bin/env python3
"""Turn the Dream FC in a DLS19 profile.dat into NK Fužinar.

Profile payload layout used here (version 200, see dls_save.py for the file wrapper):
  0x00  u32 200, u32 6150, u32 6150, u32 save counter, i32 -1, u32 1, u32 timestamp, u32 0
  0x20  u8  number of custom players N, then N records of 174 bytes (ids 0xfffe, 0xfffd, ...):
          +0x00 u16 id      +0x02 first name (17 x UTF-16)   +0x24 surname (37 x UTF-16)
          +0x74 u16 nationality   +0x76 u8 face  +0x77 u8 hair colour  +0x78 u8 skin  +0x79 u8 style
          +0x7a u8 height  +0x7d u8 group (0 GK 1 DF 2 MF 3 FW)  +0x7e/+0x7f/+0x80 u8 positions
          +0x81 u8 1  +0x82 u8 foot (0 left, 1 right)  +0x83 13 x u16 base ratings (0-1000)
          +0xa1 u16 birth date (days since 1900-01-01)
  then  u8 2, u8 1, u16 0, u32 squad size S, 32 x (u8 shirt, u8 position, u16 counter),
        32 x u32 player id (-1 empty; custom ids are 0x0000fffe...), u32 S, u32 0,
        S x (u32 id, 13 x u16 current ratings x10, u8 0)        <- development
  ...   line-up: u8 count, count x u16 id, u8 0, u8 formation, u8 ?, 5 x u16 set-piece takers
        (captain, penalties, free kicks, corners left, corners right)
  ...   stadium name (24 x UTF-16), team name (33 x UTF-16), short name
Squad members are released by leaving them out of the squad, development and line-up
lists, so their upgrades are dropped and they keep their database ratings.

Usage: python3 -I make_fuzinar_profile.py <profile.dat> <db dir (players.dat, links)> <team id> <out profile.dat>
"""
import datetime
import os
import random
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "db"))
sys.path.insert(0, os.path.dirname(__file__))
import dls_db as D  # noqa: E402
import dls_save as S  # noqa: E402

REC = 0xAE
TEAM_NAME = "NK Fužinar"
SHORT_NAME = "FUZ"
STADIUM = "Športni park Ravne"


def utf16(s, nchars):
    b = s.encode("utf-16le")[: (nchars - 1) * 2]
    return b + b"\0" * (nchars * 2 - len(b))


def group(pos):
    return 0 if pos == 0 else 1 if pos <= 7 else 2 if pos <= 18 else 3


def find_lineup(d, start, old_ids):
    """Offset of the line-up block: u8 count followed by exactly the squad's ids."""
    n = len(old_ids)
    want = set(old_ids)
    for o in range(start, len(d) - 1 - 2 * n):
        if d[o] == n:
            ids = struct.unpack_from("<%dH" % n, d, o + 1)
            if set(ids) == want:
                return o
    raise SystemExit("line-up block not found")


def main():
    src, dbdir, tid, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    hdr, d = S.load(src)
    d = bytearray(d)
    pl = D.Players(D.load(os.path.join(dbdir, "players.dat")))
    ln = D.Links(D.load(os.path.join(dbdir, "teamplayerlinks_0.dat")))
    squad = ln.teams[tid][:32]

    # ---- old layout
    n_old = d[0x20]
    p = 0x21 + n_old * REC
    sect_hdr = d[p:p + 8]
    s_old = struct.unpack_from("<I", d, p + 4)[0]
    info_o = p + 8
    ids_o = info_o + 32 * 4
    dev_o = ids_o + 32 * 4
    dev_cnt = struct.unpack_from("<I", d, dev_o)[0]
    dev_end = dev_o + 8 + dev_cnt * 31
    old_ids = [struct.unpack_from("<I", d, ids_o + 4 * i)[0] for i in range(s_old)]
    lu = find_lineup(d, dev_end, [x & 0xFFFF for x in old_ids])
    lu_n = d[lu]
    after_lu = lu + 1 + 2 * lu_n  # u8 0, u8 formation, u8 ?, then 5 x u16 takers
    takers_o = after_lu + 3

    # ---- new custom player records (Fužinar), starting XI first
    order = sorted(squad, key=lambda e: (0 if e["flags"] & 1 else 1, e["slot"]))
    new_ids = [0xFFFE - i for i in range(len(order))]
    rnd = random.Random(1937)
    recs = bytearray()
    dev = bytearray()
    info = bytearray()
    for nid, e in zip(new_ids, order):
        g = pl.get(pl.by_id[e["player_id"]])
        r = bytearray(REC)
        struct.pack_into("<H", r, 0, nid)
        r[0x02:0x24] = utf16(g["first_name"], 17)
        r[0x24:0x6E] = utf16(g["surname"], 37)
        struct.pack_into("<H", r, 0x74, g["nationality"])
        r[0x76] = rnd.randint(1, 75)       # face
        r[0x77] = rnd.randint(0, 7)        # hair colour
        r[0x78] = rnd.choice((0, 0, 1, 1, 2, 3))  # skin, mostly light
        r[0x79] = rnd.randint(1, 5)
        r[0x7A] = max(150, min(210, g["height_cm"] or 180))
        pos, pos2 = g["pos_primary"], g["pos_secondary"]
        r[0x7D] = group(pos)
        r[0x7E], r[0x7F], r[0x80] = pos, pos2, pos2
        r[0x81] = 1
        r[0x82] = 0 if g["foot"] == 0 else 1
        struct.pack_into("<13H", r, 0x83, *g["attr"])
        if g["birth_year"] and g["birth_year"] > 1900:
            bd = datetime.date(g["birth_year"], max(1, g["birth_month"]), max(1, g["birth_day"]))
            struct.pack_into("<H", r, 0xA1, (bd - datetime.date(1900, 1, 1)).days)
        else:
            struct.pack_into("<H", r, 0xA1, 0x927C)
        struct.pack_into("<H", r, 0x9F, 0x20)
        recs += r
        dev += struct.pack("<I13HB", nid, *[min(10000, a * 10) for a in g["attr"]], 0)
        info += struct.pack("<BBH", e["shirt"] or 0, pos, 0)
    info += b"\0" * (32 * 4 - len(info))
    ids = b"".join(struct.pack("<I", x) for x in new_ids) + b"\xff\xff\xff\xff" * (32 - len(new_ids))

    def taker(bit):
        for nid, e in zip(new_ids, order):
            if e["flags"] & bit:
                return nid
        return new_ids[min(len(new_ids) - 1, 10)]
    takers = struct.pack("<5H", taker(2), taker(4), taker(8), taker(0x10), taker(0x20))
    lineup = bytes([len(new_ids)]) + struct.pack("<%dH" % len(new_ids), *new_ids)

    # ---- reassemble (everything else is kept byte for byte)
    sect = bytearray(sect_hdr)
    struct.pack_into("<I", sect, 4, len(new_ids))
    dev_hdr = struct.pack("<I", len(new_ids)) + d[dev_o + 4:dev_o + 8]
    new = (d[:0x20] + bytes([len(new_ids)]) + recs + sect + info + ids + dev_hdr + dev
           + d[dev_end:lu] + lineup + d[after_lu:takers_o] + takers + d[takers_o + 10:])
    new = bytearray(new)

    # ---- names (fixed buffers, located by their current text)
    def replace_text(old, new_text, nchars):
        b = old.encode("utf-16le")
        o = new.find(b)
        if o < 0:
            print("not found:", old)
            return
        new[o:o + nchars * 2] = utf16(new_text, nchars)
    for old, txt, n in (("Lakeside Park", STADIUM, 24), ("Balkhash Kazakhstan", TEAM_NAME, 33)):
        replace_text(old, txt, n)
    o = new.find("BKH".encode("utf-16le"))
    if o >= 0:
        new[o:o + 8] = utf16(SHORT_NAME, 4)

    S.dump(out, bytes(new))
    print(f"{n_old} custom players -> {len(new_ids)} Fužinar players; released {s_old - n_old} signed players; "
          f"payload {len(d)} -> {len(new)} bytes")


if __name__ == "__main__":
    main()
