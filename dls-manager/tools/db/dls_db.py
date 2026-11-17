#!/usr/bin/env python3
"""Read (and later write) Dream League Soccer 2019 database files.

DB files live in the APK at assets/data/db/*.dat. Each file is a single
zlib stream. See docs/formats/players_dat.md for the record layout.

Usage:
  python3 -I dls_db.py dump-players <players.dat> [--csv out.csv] [--limit N]
"""
import argparse
import csv
import struct
import sys
import zlib

PLAYER_RECORD_SIZE_V8 = 180  # players.dat (header version 8)
PLAYER_RECORD_SIZE_V6 = 184  # players_3050.dat (header version 6) - layout not yet mapped

# Offsets inside a v8 player record (180 bytes). "?" = meaning not confirmed yet.
F = {
    "id": (0x00, "H"),
    "first_name": (0x02, 17),        # UTF-16LE, 17 chars
    "surname": (0x24, 37),           # UTF-16LE, 37 chars
    "nationality": (0x6E, "H"),
    "unk_70": (0x70, "H"),           # ? 0-8 (skin tone?)
    "unk_72": (0x72, "H"),           # ? 1-73 (face/hair model?)
    "unk_74": (0x74, "H"),           # ? 0-7 (hair colour?)
    "unk_76": (0x76, "H"),           # ? 0-5 (position group?)
    "height_cm": (0x78, "H"),
    "weight_kg": (0x7A, "H"),
    "unk_7c": (0x7C, "H"),
    "unk_7e": (0x7E, "H"),
    "unk_80": (0x80, "H"),
    "unk_82": (0x82, "H"),
    "foot": (0x84, "H"),             # ? 0/1/2/3 (1 most common -> right?)
    # 13 ability ratings, 0..1000. Order to be confirmed against in-game screens.
    "attr": (0x86, 13),
    "unk_a0": (0xA0, "H"),
    "unk_a2": (0xA2, "H"),
    "unk_a4": (0xA4, "H"),
    "unk_a6": (0xA6, "H"),
    "birth_day": (0xA8, "H"),
    "birth_month": (0xAC, "H"),
    "birth_year": (0xB0, "H"),       # 1900 = unknown
}


def load(path):
    raw = open(path, "rb").read()
    return zlib.decompress(raw) if raw[:2] == b"\x78\x9c" else raw


def parse_players(data):
    magic, version, count = struct.unpack_from("<III", data, 0)
    size = {8: PLAYER_RECORD_SIZE_V8, 6: PLAYER_RECORD_SIZE_V6}.get(version)
    if size is None or 12 + size * count != len(data):
        raise ValueError(f"unexpected players header: magic={magic} version={version} count={count} len={len(data)}")
    if version != 8:
        raise NotImplementedError("only v8 (players.dat) layout is mapped so far")
    out = []
    for i in range(count):
        r = data[12 + size * i: 12 + size * (i + 1)]
        p = {}
        for k, (off, fmt) in F.items():
            if k in ("first_name", "surname"):
                p[k] = r[off:off + fmt * 2].decode("utf-16le").split("\0")[0]
            elif k == "attr":
                p[k] = list(struct.unpack_from("<%dH" % fmt, r, off))
            else:
                p[k] = struct.unpack_from("<" + fmt, r, off)[0]
        out.append(p)
    return {"magic": magic, "version": version, "players": out}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump-players")
    d.add_argument("path")
    d.add_argument("--csv")
    d.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()

    db = parse_players(load(a.path))
    players = db["players"]
    print(f"version {db['version']}, {len(players)} players", file=sys.stderr)
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            keys = [k for k in F if k != "attr"]
            w.writerow(keys + [f"attr{i}" for i in range(13)])
            for p in players:
                w.writerow([p[k] for k in keys] + p["attr"])
    for p in players[: a.limit]:
        print(p["id"], p["first_name"], p["surname"], p["height_cm"], p["weight_kg"],
              f"{p['birth_day']}/{p['birth_month']}/{p['birth_year']}", p["attr"])


if __name__ == "__main__":
    main()
