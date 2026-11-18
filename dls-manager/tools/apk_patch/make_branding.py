#!/usr/bin/env python3
"""Assistant Manager 27 branding: the AM27 logo, the launcher icons and the loading pictures.

  logo      assets/ui/am27_logo.png: "AM" in white and "27" in the game's green, heavy Manrope,
            with a soft shadow so it reads over the paintings.
  icons     res/mipmap-*/ic_launcher{,_round,_background,_foreground}.png at the sizes the
            original APK has. Adaptive icons (Android 8+): the painting is the background
            layer, the logo the foreground, inside the 66% safe zone. Legacy and round icons
            are the two composited (round: circle-masked).
  loading   assets/ui/load_*.jpg, the paintings the loading screen fades between (≤1600 px wide).

Usage: python3 -I make_branding.py --font Manrope-800.ttf --icon-src martial.png
           --pictures a.jpg b.jpg ... --out-res res_dir --out-ui assets/ui
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

GREEN = (76, 200, 106, 255)
DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def logo(font, h):
    """AM27 wordmark, h px tall (transparent)."""
    f = ImageFont.truetype(font, int(h * 1.18))
    a, b = "AM", "27"
    wa = f.getlength(a)
    wb = f.getlength(b)
    gap = h * 0.04
    pad = int(h * 0.22)
    W = int(wa + gap + wb) + pad * 2
    H = h + pad * 2
    top = pad - f.getbbox("AM27")[1]
    text = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(text)
    d.text((pad, top), a, font=f, fill=(255, 255, 255, 255))
    d.text((pad + wa + gap, top), b, font=f, fill=GREEN)
    # a bar under the 27
    by = pad + h + int(h * 0.06)
    d.rounded_rectangle((pad + wa + gap + h * 0.04, by, pad + wa + gap + wb - h * 0.04, by + max(2, int(h * 0.07))), radius=int(h * 0.04), fill=GREEN)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(text.getchannel("A").point(lambda v: int(v * 0.65)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(h * 0.06))
    out = Image.new("RGBA", (W, H))
    out.alpha_composite(shadow, (0, int(h * 0.03)))
    out.alpha_composite(text)
    return out.crop(out.getbbox())


def cover(img, size, cx=0.5, cy=0.5, zoom=1.0):
    W, H = img.size
    s = max(size / W, size / H) * zoom
    im = img.resize((max(size, round(W * s)), max(size, round(H * s))), Image.LANCZOS)
    x = int((im.width - size) * cx)
    y = int((im.height - size) * cy)
    return im.crop((x, y, x + size, y + size))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--icon-src", required=True)
    ap.add_argument("--pictures", nargs="+", required=True)
    ap.add_argument("--out-res", required=True)
    ap.add_argument("--out-ui", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_ui, exist_ok=True)
    logo(a.font, 220).save(os.path.join(a.out_ui, "am27_logo.png"), optimize=True)
    src = Image.open(a.icon_src).convert("RGBA")
    for dn, k in DENS.items():
        d = os.path.join(a.out_res, "mipmap-" + dn)
        os.makedirs(d, exist_ok=True)
        full = int(108 * k)     # adaptive layers: 108dp, safe zone the middle 66dp
        # the painting is landscape with his face near the top: show it a little smaller and
        # lower, over a blurred copy, so masks (circles, squircles) keep the whole head
        base = cover(src, full, cx=0.56, cy=0.0, zoom=1.0)
        bg = base.filter(ImageFilter.GaussianBlur(full * 0.05))
        inner = cover(src, int(full * 0.86), cx=0.56, cy=0.0, zoom=1.0)
        fade = Image.new("L", inner.size, 255)
        fd = ImageDraw.Draw(fade)
        e = int(inner.width * 0.12)
        for i in range(e):
            v = int(255 * i / e)
            fd.rectangle((i, i, inner.width - 1 - i, inner.height - 1 - i), outline=v)
        bg.paste(inner, ((full - inner.width) // 2, int(full * 0.17)), fade)
        # darken the lower half a little so the logo stands out
        shade = Image.new("RGBA", (full, full))
        sd = ImageDraw.Draw(shade)
        for y in range(full):
            t = max(0.0, (y / full - 0.35) / 0.65)
            sd.line((0, y, full, y), fill=(0, 0, 0, int(150 * t)))
        bg.alpha_composite(shade)
        fg = Image.new("RGBA", (full, full))
        lg = logo(a.font, int(full * 0.2))
        lg.thumbnail((int(full * 0.58), full), Image.LANCZOS)
        fg.alpha_composite(lg, ((full - lg.width) // 2, int(full * 0.79) - lg.height))
        bg.save(os.path.join(d, "ic_launcher_background.png"), optimize=True)
        fg.save(os.path.join(d, "ic_launcher_foreground.png"), optimize=True)
        legacy = int(48 * k)
        comp = bg.copy()
        comp.alpha_composite(fg)
        # legacy icons show the middle 72/108 of the adaptive art
        m = int(full * 10 / 108)
        comp = comp.crop((m, m, full - m, full - m)).resize((legacy, legacy), Image.LANCZOS)
        sq = Image.new("RGBA", (legacy, legacy))
        mask = Image.new("L", (legacy, legacy))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, legacy - 1, legacy - 1), radius=int(legacy * 0.18), fill=255)
        sq.paste(comp, (0, 0), mask)
        sq.save(os.path.join(d, "ic_launcher.png"), optimize=True)
        rd = Image.new("RGBA", (legacy, legacy))
        cm = Image.new("L", (legacy, legacy))
        ImageDraw.Draw(cm).ellipse((0, 0, legacy - 1, legacy - 1), fill=255)
        rd.paste(comp, (0, 0), cm)
        rd.save(os.path.join(d, "ic_launcher_round.png"), optimize=True)
    for i, p in enumerate(a.pictures):
        im = Image.open(p).convert("RGB")
        im.thumbnail((1600, 1600), Image.LANCZOS)
        im.save(os.path.join(a.out_ui, "load_%d.jpg" % (i + 1)), quality=82, optimize=True, progressive=True)
    print("logo, icons and", len(a.pictures), "loading pictures written")


if __name__ == "__main__":
    main()
