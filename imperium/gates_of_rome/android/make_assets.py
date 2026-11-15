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

# the icon: a torch-lit arch of a city gate, on night blue
def icon(n):
    s = 4 * n
    im = Image.new("RGBA", (s, s), (13, 16, 24, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([s * .2, s * .25, s * .8, s * .85], fill=(240, 145, 58, 255))
    stone = (190, 180, 160, 255)
    d.rectangle([s * .12, s * .3, s * .3, s * .92], fill=stone); d.rectangle([s * .7, s * .3, s * .88, s * .92], fill=stone)
    d.rectangle([s * .12, s * .22, s * .88, s * .34], fill=stone)
    d.pieslice([s * .3, s * .3, s * .7, s * .7], 180, 360, fill=stone)
    d.rectangle([s * .36, s * .5, s * .64, s * .92], fill=(13, 16, 24, 255))
    d.pieslice([s * .36, s * .36, s * .64, s * .64], 180, 360, fill=(13, 16, 24, 255))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=s * .22, fill=255)
    im.putalpha(mask)
    return im.resize((n, n), Image.LANCZOS)

for name, n in {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}.items():
    d = os.path.join(res, "mipmap-" + name)
    os.makedirs(d, exist_ok=True)
    icon(n).save(os.path.join(d, "ic_launcher.png"))
print("assets ready")
