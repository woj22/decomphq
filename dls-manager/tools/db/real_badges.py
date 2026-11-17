#!/usr/bin/env python3
"""Make DLS19 draw each team's real badge image instead of a generated one.

A team record's byte at 0x132 (copied to +0x12e of the in-memory team by FUN_000ad090) picks
the badge: 0-28 = a generated badge from the logo_<n><a-c>_mask.png templates, -1 = the team's
image (FUN_00166a78: imported DOCS:t<id>.png, else PKG:Data/FE/teams/t<id>.png). Every team that
has a t<id>.png in the given folder is set to -1. The player's team (258) gets the same from the
native patch at 0xb2d2c (see patch_apk.py).

Usage: python3 -I real_badges.py <teams.dat> <folder with t<id>.png>   (rewrites teams.dat)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dls_db as D  # noqa: E402

BADGE_STYLE = 0x132


def main():
    path, folder = sys.argv[1], sys.argv[2]
    tm = D.Teams(D.load(path))
    have = {int(m.group(1)) for f in os.listdir(folder) for m in [re.match(r"t(\d+)\.png$", f)] if m}
    n = 0
    for tid, r in tm.by_id.items():
        if tid in have and r[BADGE_STYLE] != 0xFF:
            r[BADGE_STYLE] = 0xFF
            n += 1
    D.save_zlib(path, tm.to_bytes())
    print(f"{n} teams switched to their badge image ({len(have)} images, {len(tm.recs)} teams)")


if __name__ == "__main__":
    main()
