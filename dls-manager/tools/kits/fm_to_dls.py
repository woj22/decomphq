#!/usr/bin/env python3
"""Convert Football Manager kit renders (front view of the shirt, 420x420) into DLS19 kit
textures (512x512), using a DLS19 kit as the panel template.

DLS19 kit texture layout (measured on DLS19 Barcelona/Real Madrid kits):
  centre strip x 165-350: the torso unfolded over the shoulders. y 0-182 is the BACK (upside
      down, hem at the top), y 182 is the shoulder seam, y 182-378 is the FRONT (collar to hem).
      The strip also wraps round the sides, so the chest (crest, maker logo) only spans the
      middle ~60%.
  four sleeve pieces: top-left/top-right corners and the two side pieces next to the strip.
  y 270-378 left/right of the strip: socks.  y 380-512: shorts (left and right halves).
  small swatch at x 470-497, y 250-265: number colour.
The template's alpha channel decides where paint lands.

FM renders only show the shirt front, so: front panel = FM shirt body (scaled into the chest
area, sides filled with the shirt's plain pattern), back = the plain lower part of the shirt
(no crest or sponsor), sleeves = FM sleeve, shorts/socks = colours from Wikipedia's kit
infobox (shorts1/socks1 for home, 2 for away, 3 for third), else the shirt's main colour.

Usage:
  python3 -I fm_to_dls.py --template <dls19 kit.png> --fm <dir with FM pngs> --wiki <dir of .wiki pages>
                          --map <json {fm file stem: [club id, wiki title]}> --slots <slots.json> --out <dir>
Writes <out>/<team id>_home.png / _away.png / _third.png and <out>/preview.png.
"""
import argparse
import json
import os
import re

import numpy as np
from PIL import Image, ImageFilter

# FM render geometry (identical for every FM kit render)
FM_BODY = (125, 25, 294, 395)        # x0, y0, x1, y1: shirt body, collar to hem
FM_PLAIN = (135, 300, 284, 388)      # bottom quarter of the body: just the shirt pattern
FM_SLEEVE_L = (72, 100, 120, 182)    # inside the left sleeve
FM_SLEEVE_R = (299, 100, 347, 182)

# DLS19 template geometry
STRIP_X = (165, 350)
SEAM_Y = 182
HEM_Y = 378
CHEST_W = 0.62                       # fraction of the strip width the FM body front covers
SLEEVES = [(0, 0, 162, 128), (70, 112, 165, 268), (352, 0, 512, 128), (350, 112, 444, 268)]
SOCKS = [(0, 268, 165, 380), (350, 268, 512, 380)]
SHORTS = [(0, 380, 512, 512)]
SWATCH = (466, 246, 500, 268)

KIT_NAMES = {"1": "home", "2": "away", "3": "third"}


def wiki_colours(text, n):
    def field(name):
        m = re.search(r"\|\s*%s%s\s*=\s*#?([0-9A-Fa-f]{6})" % (name, n), text)
        return tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)) if m else None
    return field("shorts"), field("socks")


def dominant(img):
    a = np.asarray(img.convert("RGB")).reshape(-1, 3)
    q = (a // 24) * 24 + 12
    vals, counts = np.unique(q, axis=0, return_counts=True)
    return tuple(int(v) for v in vals[counts.argmax()])


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def convert(template, fm_path, shorts, socks):
    fm = Image.open(fm_path).convert("RGBA").resize((420, 420), Image.LANCZOS)
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    plain = fm.crop(FM_PLAIN).convert("RGB")
    main = dominant(plain)
    flat = Image.new("RGBA", fm.size, main + (255,))  # see-through bits (round the collar) -> shirt colour
    flat.alpha_composite(fm)
    fm = flat
    body = fm.crop(FM_BODY).convert("RGB")

    x0, x1 = STRIP_X
    sw = x1 - x0
    # back: plain pattern, upside down (hem at the top of the texture)
    out.paste(plain.resize((sw, SEAM_Y), Image.LANCZOS).transpose(Image.FLIP_TOP_BOTTOM), (x0, 0))
    # front: FM body over the chest. The sides (the strip wraps round the body) get each row's
    # typical colour across the shirt (per-row median), which keeps horizontal pinstripes and
    # hoops but not a sash, piping or logos.
    cw = int(round(sw * CHEST_W))
    fh = HEM_Y - SEAM_Y
    front = np.asarray(body.resize((cw, fh), Image.LANCZOS)).astype(float)
    rowcol = np.median(front[:, 6:cw - 6], axis=1)  # (fh, 3)
    row = np.repeat(rowcol[:, None, :], sw, axis=1)
    left = (sw - cw) // 2
    ramp = np.ones(cw)
    edge = max(4, cw // 10)
    ramp[:edge] = np.linspace(0, 1, edge)
    ramp[-edge:] = np.linspace(1, 0, edge)
    seg = row[:, left:left + cw]
    row[:, left:left + cw] = seg * (1 - ramp[None, :, None]) + front * ramp[None, :, None]
    out.paste(Image.fromarray(row.clip(0, 255).astype("uint8")), (x0, SEAM_Y))

    # sleeves (left pieces from the FM left sleeve, right pieces from the right sleeve)
    for i, box in enumerate(SLEEVES):
        src = fm.crop(FM_SLEEVE_L if box[0] < 256 else FM_SLEEVE_R).convert("RGB")
        out.paste(src.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])

    for boxes, col in ((SOCKS, socks or main), (SHORTS, shorts or main)):
        for box in boxes:
            out.paste(col + (255,), box)
    number = (17, 17, 17) if lum(main) > 150 else (255, 255, 255)
    out.paste(number + (255,), SWATCH)

    # keep only the template's panels; soften the seams a little
    alpha = template.getchannel("A")
    out.putalpha(alpha)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--fm", required=True, nargs="+")
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--slots", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    template = Image.open(a.template).convert("RGBA").resize((512, 512), Image.LANCZOS)
    cmap = json.load(open(a.map, encoding="utf-8"))
    slots = json.load(open(a.slots, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)

    files = {}
    for d in a.fm:  # later dirs win for duplicate names (pass the newest pack last)
        for f in os.listdir(d):
            m = re.match(r"(.+?)([123])\.png$", f, re.I)
            if m:
                files[(m.group(1).lower(), m.group(2))] = os.path.join(d, f)

    done = []
    for (stem, n), path in sorted(files.items()):
        if stem not in cmap:
            continue
        cid, title = cmap[stem]
        tid = slots[cid]
        wpath = os.path.join(a.wiki, title + ".wiki")
        text = open(wpath, encoding="utf-8").read() if os.path.exists(wpath) else ""
        shorts, socks = wiki_colours(text, n)
        img = convert(template, path, shorts, socks)
        name = "%d_%s.png" % (tid, KIT_NAMES[n])
        img.save(os.path.join(a.out, name))
        done.append((cid, n, name, img))
        print(f"{cid:20s} {KIT_NAMES[n]:5s} -> {name}  shorts={shorts} socks={socks}")

    # contact sheet: each kit on a grey background, 4 per row
    cols = 4
    rows = (len(done) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 260, rows * 260), (60, 60, 60))
    for i, (_, _, _, img) in enumerate(done):
        bg = Image.new("RGB", (512, 512), (60, 60, 60))
        bg.paste(img, (0, 0), img)
        sheet.paste(bg.resize((256, 256)), ((i % cols) * 260 + 2, (i // cols) * 260 + 2))
    sheet.save(os.path.join(a.out, "preview.png"))
    print(len(done), "kits")


if __name__ == "__main__":
    main()
