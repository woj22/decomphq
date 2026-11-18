#!/usr/bin/env python3
"""Silence the start-up toasts (an apktool-decoded smali tree, edited in place).

The modded base APK pops up a chain of toasts as it starts: the "LITEAPKS.COM & 9MOD.COM"
banner in MainActivity.onCreate and one from each android/system/licensing class; our own
save restore in com/savegame/SavesRestoring adds "Setting up DLS Manager…" / "Ready.". Each
Toast.show() there becomes a nop (the toasts are still built, never shown; nothing else
changes). The game's own toasts elsewhere are left alone.

Usage: python3 -I no_toasts.py <decoded dir>   (then apktool b, take classes.dex / classes2.dex)
"""
import glob
import os
import re
import sys

SHOW = re.compile(r"\n(\s*)invoke-virtual \{v\d+\}, Landroid/widget/Toast;->show\(\)V")


def main():
    d = sys.argv[1]
    files = glob.glob(os.path.join(d, "smali*/android/system/licensing/*.smali")) + \
        glob.glob(os.path.join(d, "smali*/com/savegame/SavesRestoring.smali")) + \
        glob.glob(os.path.join(d, "smali*/com/firsttouchgames/dls3/MainActivity.smali"))
    total = 0
    for f in files:
        s = open(f, encoding="utf-8").read()
        s, n = SHOW.subn(r"\n\1nop", s)
        if n:
            open(f, "w", encoding="utf-8").write(s)
        total += n
    print(total, "toasts silenced in", len(files), "classes")


if __name__ == "__main__":
    main()
