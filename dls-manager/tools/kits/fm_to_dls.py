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
FM_PLAIN = (135, 300, 284, 372)      # lower body above the hem trim: just the shirt pattern
FM_SLEEVE_L = (72, 100, 120, 182)    # inside the left sleeve
FM_SLEEVE_R = (299, 100, 347, 182)

# DLS19 template geometry
STRIP_X = (165, 350)
SEAM_Y = 182
HEM_Y = 378
SCALE = (378 - 182) / (395 - 25)     # FM px -> DLS px, the same in x and y (no stretching)
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


def clean_pattern(img, ref=None, thresh=70, grow=3):
    """Drop one-off decoration (a sash, logos, their soft edges) from a patch of shirt.

    A pixel is the shirt's pattern if it is close to its row's median (hoops, pinstripes) or
    to its column's median (vertical stripes); otherwise it is replaced by the row median.
    Subtle checks stay because they never differ much from either median."""
    a = np.asarray(img).astype(float)
    rmed = np.median(a, axis=1, keepdims=True)
    cmed = np.median(a, axis=0, keepdims=True)
    dr = np.abs(a - rmed).sum(2)
    dc = np.abs(a - cmed).sum(2)
    # a column counts as a vertical stripe only if it keeps that colour down most of a taller
    # slice of the shirt (ref): a diagonal sash covers any one column for part of it only
    # A stripe stays put all the way down; a diagonal sash moves sideways, so check the upper
    # and lower halves of the taller slice separately.
    r = np.asarray(ref).astype(float) if ref is not None else a
    hit = np.abs(r - cmed).sum(2) <= thresh
    half = hit.shape[0] // 2
    stripe_col = (hit[:half].mean(axis=0) > 0.7) & (hit[half:].mean(axis=0) > 0.7)
    bad = (dr > thresh) & ((dc > thresh) | ~stripe_col[None, :])
    heavy = bad.mean() > 0.08  # measured before growing the mask
    for _ in range(grow):  # include the blended edge pixels around the decoration
        b = bad.copy()
        b[1:] |= bad[:-1]; b[:-1] |= bad[1:]; b[:, 1:] |= bad[:, :-1]; b[:, :-1] |= bad[:, 1:]
        bad = b
    if heavy:
        # lots of decoration (e.g. a sash): any patched-up texture would show seams when
        # repeated, so use the rows' own colours only (keeps hoops and pinstripes)
        out = np.broadcast_to(rmed, a.shape)
    else:
        out = np.where(bad[..., None], np.broadcast_to(rmed, a.shape), a)
    return Image.fromarray(np.ascontiguousarray(out).clip(0, 255).astype("uint8"))


def tile(img, w, h):
    """Fill w x h by repeating img, mirrored on alternate tiles so edges always match."""
    a = np.asarray(img)
    a = np.concatenate([a, a[:, ::-1]], axis=1)
    a = np.concatenate([a, a[::-1]], axis=0)
    ry, rx = h // a.shape[0] + 1, w // a.shape[1] + 1
    return Image.fromarray(np.tile(a, (ry, rx, 1))[:h, :w])


def flatten_shading(img, radius=12):
    """Remove soft fold/lighting shading from a render, keeping the fine pattern."""
    a = np.asarray(img).astype(float)
    blur = np.asarray(img.filter(ImageFilter.GaussianBlur(radius))).astype(float)
    out = a - blur + blur.reshape(-1, 3).mean(0)
    return Image.fromarray(out.clip(0, 255).astype("uint8"))


def convert(template, fm_path, shorts, socks):
    fm = Image.open(fm_path).convert("RGBA").resize((420, 420), Image.LANCZOS)
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    plain = fm.crop(FM_PLAIN).convert("RGB")
    main = dominant(plain)
    plain = clean_pattern(plain, fm.crop((FM_PLAIN[0], 200, FM_PLAIN[2], FM_PLAIN[3])).convert("RGB"))
    flat = Image.new("RGBA", fm.size, main + (255,))  # see-through bits (round the collar) -> shirt colour
    flat.alpha_composite(fm)
    fm = flat
    body = fm.crop(FM_BODY).convert("RGB")

    x0, x1 = STRIP_X
    sw = x1 - x0
    fh = HEM_Y - SEAM_Y
    # back: the plain shirt pattern repeated at its true size (mirror-tiled, so no seams),
    # upside down like the template (hem at the top of the texture)
    pw, ph = round(plain.width * SCALE), round(plain.height * SCALE)
    out.paste(tile(plain.resize((pw, ph), Image.LANCZOS), sw, SEAM_Y).transpose(Image.FLIP_TOP_BOTTOM), (x0, 0))
    # front: FM body at the same scale in x and y, centred. The strip also wraps round the
    # sides of the body, so the shirt's own pattern is continued outward from both edges: the
    # front with logos/sash cleaned out, mirrored at the edge so it joins without a seam (as in
    # real DLS kits, where stripes/hoops/checks run across the whole panel).
    cw = round(body.width * SCALE)
    front_img = body.resize((cw, fh), Image.LANCZOS)
    trim = 3  # skip the render's shaded outline at the shirt's edge
    inner = front_img.crop((trim, 0, cw - trim, fh))
    clean = np.asarray(clean_pattern(inner)).astype(float)
    front = np.asarray(front_img).astype(float)
    W = clean.shape[1]
    left = (sw - cw) // 2

    def mirror_col(k, from_left):  # k = distance outward from the edge (0 = next to it)
        i = k % (2 * W)
        i = i if i < W else 2 * W - 1 - i
        return i if from_left else W - 1 - i

    row = np.zeros((fh, sw, 3))
    for x in range(sw):
        if x < left + trim:
            row[:, x] = clean[:, mirror_col(left + trim - 1 - x, True)]
        elif x >= left + cw - trim:
            row[:, x] = clean[:, mirror_col(x - (left + cw - trim), False)]
        else:
            row[:, x] = front[:, x - left]
    # soften the join between the real front and its continuation
    edge = max(4, cw // 12)
    for j in range(edge):
        a = (j + 1) / (edge + 1)
        xl, xr = left + trim + j, left + cw - trim - 1 - j
        row[:, xl] = a * front[:, xl - left] + (1 - a) * clean[:, j]
        row[:, xr] = a * front[:, xr - left] + (1 - a) * clean[:, W - 1 - j]
    out.paste(Image.fromarray(row.clip(0, 255).astype("uint8")), (x0, SEAM_Y))

    # sleeves: the shirt's plain pattern at true size; if the FM sleeves are clearly another
    # colour than the body (contrast sleeves), a flat fill in that colour instead
    sp = plain.resize((pw, ph), Image.LANCZOS)
    for box in SLEEVES:
        sl = dominant(fm.crop(FM_SLEEVE_L if box[0] < 256 else FM_SLEEVE_R))
        w, h = box[2] - box[0], box[3] - box[1]
        if sum(abs(a - b) for a, b in zip(sl, main)) > 120:
            out.paste(sl + (255,), box)
        else:
            out.paste(tile(sp, w, h), box[:2])

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
