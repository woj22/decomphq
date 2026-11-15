"""Turn the published game page into the app's index.html (offline three.js, a full HTML document) and draw the icon."""
import os
import shutil
import sys

from PIL import Image, ImageDraw

page, three, assets, res = sys.argv[1:5]
html = open(page, encoding="utf-8").read()
cdn = '<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>'
assert cdn in html
html = html.replace(cdn, '<script src="three.min.js"></script>')
doc = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
       '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}'
       'img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + html + '</body></html>')
os.makedirs(assets, exist_ok=True)
open(os.path.join(assets, "index.html"), "w", encoding="utf-8").write(doc)
shutil.copy(three, os.path.join(assets, "three.min.js"))

# the icon: a gold crown over the glowing caldera, on basalt
def icon(n):
    s = 4 * n
    im = Image.new("RGBA", (s, s), (20, 16, 14, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([s * .1, s * .58, s * .9, s * 1.05], fill=(255, 106, 26, 255))
    d.polygon([(s * .05, s), (s * .38, s * .62), (s * .62, s * .62), (s * .95, s)], fill=(43, 34, 32, 255))
    gold = (216, 168, 74, 255)
    d.polygon([(s * .24, s * .52), (s * .2, s * .22), (s * .37, s * .36), (s * .5, s * .14), (s * .63, s * .36), (s * .8, s * .22), (s * .76, s * .52)], fill=gold)
    d.rectangle([s * .24, s * .5, s * .76, s * .58], fill=gold)
    for x in (.2, .5, .8):
        d.ellipse([s * x - s * .035, s * (.22 if x != .5 else .14) - s * .035, s * x + s * .035, s * (.22 if x != .5 else .14) + s * .035], fill=(239, 227, 204, 255))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=s * .22, fill=255)
    im.putalpha(mask)
    return im.resize((n, n), Image.LANCZOS)

for name, n in {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}.items():
    d = os.path.join(res, "mipmap-" + name)
    os.makedirs(d, exist_ok=True)
    icon(n).save(os.path.join(d, "ic_launcher.png"))
print("assets ready")
