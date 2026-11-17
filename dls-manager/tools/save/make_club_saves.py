#!/usr/bin/env python3
"""Build the pre-made club saves (assets/dlsmgr/clubsaves/<club>.dat).

A DLS19 season stores per-player competition stats, and each entry is read in a longer form
when that player is in the user's squad (FUN_0026f6fc asks FUN_000ae0f0(0x102)). Swapping the
squad in the file therefore puts every later read out of step (the v37-v44 crash in
FUN_0026ae38). So, for every club:
  1. Profile.becomeClub (the Java conversion) swaps squad, development, line-up and names;
  2. emu_load.py loads that file with the game's own loader under Unicorn, reading the
     competitions with the base save's squad (the one they were written with), then writes
     it back out with the game's own writer, which encodes them for the new squad;
  3. the result is loaded once more under emulation and must read to the end with a good
     checksum.

Usage: python3 -I make_club_saves.py <libDLS19.so> <base profile.dat> <clubs.json> <out dir>
(needs javac/java with org.json on JSON_JAR, and unicorn + pyelftools)
"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")


def main():
    lib, base, clubs, out = sys.argv[1:5]
    jar = os.environ["JSON_JAR"]
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp()
    cls = os.path.join(tmp, "cls")
    raw = os.path.join(tmp, "raw")
    subprocess.run(["javac", "-cp", jar, "-d", cls, os.path.join(ROOT, "android/src/com/dlsmgr/Profile.java"),
                    os.path.join(HERE, "ConvertAll.java")], check=True)
    subprocess.run(["java", "-cp", cls + os.pathsep + jar, "com.dlsmgr.ConvertAll", base, clubs, raw], check=True)
    emu = os.path.join(HERE, "emu_load.py")

    def one(name):
        cid = name[:-4]
        dst = os.path.join(out, name)
        r = subprocess.run([sys.executable, "-I", emu, lib, os.path.join(raw, name), "--comp-squad-from", base,
                            "--keep-squad", "--rewrite", dst], capture_output=True, text=True)
        if r.returncode != 0:
            return cid, "rewrite failed: " + r.stdout[-300:]
        r = subprocess.run([sys.executable, "-I", emu, lib, dst], capture_output=True, text=True)
        if r.returncode != 0 or "checksum OK" not in r.stdout:
            os.remove(dst)
            return cid, "check failed: " + r.stdout[-300:]
        return cid, "ok"
    with ThreadPoolExecutor(os.cpu_count() or 2) as ex:
        res = list(ex.map(one, sorted(os.listdir(raw))))
    bad = [r for r in res if r[1] != "ok"]
    for cid, msg in bad:
        print(cid, msg)
    print(f"{len(res) - len(bad)} of {len(res)} club saves built and checked -> {out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
