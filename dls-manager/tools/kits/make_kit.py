#!/usr/bin/env python3
"""Draw a DLS19 kit texture (512x512) from a simple design: base colour, trim colour, collar,
adidas-style three stripes (shoulders to cuffs, shorts, socks), crest and sponsor.

Panel geometry (from DLS19 Barcelona/Real Madrid kits, see fm_to_dls.py):
  torso strip x 165-350: back y 0-182 (upside down), shoulder seam y 182, front y 182-378.
  sleeves: side pieces x 70-165 / 350-444, y 112-268 (armhole on the inner edge, cuff on the
      outer edge, shoulder line through the middle at the seam height); corner pieces
      x 0-162 / 352-512, y 0-128 (shoulder line at y ~65).
  collar: thin piece x 337-348, y 0-116.
  socks: y 268-380 left/right of the strip (top of the sock at the inner edge).
  shorts: y 380-512.
Stripe positions for shorts and socks are copied from the template kit's own three stripes
(--stripes-from: a DLS19 adidas kit whose stripes are a distinct colour, e.g. Real Madrid).

Usage:
  python3 -I make_kit.py --template <dls19 kit.png> --stripes-from <dls19 adidas kit.png>
      --base 1f3768 --trim c6a14a --crest crest.png --sponsor sponsor.png --out kit.png
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw

SEAM_Y = 182
STRIP_X = (165, 350)
PANELS = [(0, 0, 512, 512)]
SLEEVE_SIDE = [(70, 165), (350, 444)]
SLEEVE_CORNER = [(0, 162), (352, 512)]
STRIPE_W, STRIPE_GAP = 3, 4
SWATCH = (466, 246, 500, 268)
COLLAR = (336, 0, 349, 117)      # the collar's own piece (gold on the Real Madrid kit)


def hexcol(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def three(y_mid):
    """y ranges of three stripes centred on y_mid."""
    step = STRIPE_W + STRIPE_GAP
    return [(y_mid - step + k * step - STRIPE_W // 2, y_mid - step + k * step - STRIPE_W // 2 + STRIPE_W)
            for k in range(3)]


def stripe_columns(ref, box):
    """Columns inside box where the reference kit has a long vertical stripe of its trim colour."""
    a = np.asarray(ref.convert("RGBA")).astype(int)
    x0, y0, x1, y1 = box
    r, g, b, al = (a[y0:y1, x0:x1, i] for i in range(4))
    gold = (r - b > 50) & (g - b > 25) & (al > 100)
    return [x0 + i for i in np.where(gold.mean(axis=0) > 0.6)[0]]


def paste_centred(img, logo, cx, cy, w):
    h = round(logo.height * w / logo.width)
    lg = logo.resize((w, h), Image.LANCZOS)
    img.alpha_composite(lg, (round(cx - w / 2), round(cy - h / 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--stripes-from", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--trim", required=True)
    ap.add_argument("--crest")
    ap.add_argument("--crest-pos", default="287,218,54", help="cx,cy,width on the front (as seen from the front; crest on the wearer's left = texture right). Render the crest at exactly this width for a sharp result")
    ap.add_argument("--sponsor")
    ap.add_argument("--sponsor-pos", default="257,282,46")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    template = Image.open(a.template).convert("RGBA").resize((512, 512), Image.LANCZOS)
    ref = Image.open(a.stripes_from).convert("RGBA").resize((512, 512), Image.LANCZOS)
    base, trim = hexcol(a.base), hexcol(a.trim)

    img = Image.new("RGBA", (512, 512), base + (255,))
    d = ImageDraw.Draw(img)

    # three stripes over the shoulders (collar to armhole), continuing down both sleeves
    for y0, y1 in three(SEAM_Y):
        d.rectangle([STRIP_X[0], y0, STRIP_X[1], y1 - 1], fill=trim)
        for x0, x1 in SLEEVE_SIDE:
            d.rectangle([x0, y0, x1, y1 - 1], fill=trim)
    for y0, y1 in three(65):
        for x0, x1 in SLEEVE_CORNER:
            d.rectangle([x0, y0, x1, y1 - 1], fill=trim)

    # collar: its own thin piece of the texture, top right of the back strip
    d.rectangle(COLLAR, fill=trim)

    # shorts and socks: copy the reference kit's stripe columns
    for box in ((0, 380, 256, 512), (256, 380, 512, 512), (0, 268, 165, 380), (350, 268, 512, 380)):
        for x in stripe_columns(ref, box):
            d.line([x, box[1], x, box[3]], fill=trim)

    d.rectangle(SWATCH, fill=trim)  # shirt number colour

    if a.crest:
        cx_, cy_, w_ = (int(v) for v in a.crest_pos.split(","))
        paste_centred(img, Image.open(a.crest).convert("RGBA"), cx_, cy_, w_)
    if a.sponsor:
        cx_, cy_, w_ = (int(v) for v in a.sponsor_pos.split(","))
        paste_centred(img, Image.open(a.sponsor).convert("RGBA"), cx_, cy_, w_)

    img.putalpha(template.getchannel("A"))
    img.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
