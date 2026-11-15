"""The campaign map in a grand-strategy parchment style: a torn parchment sheet on a dark wooden table, a muted
grey-green sea, bare cream parchment for unclaimed land, realms in solid muted colours with darker edges, ink
borders and coasts, and big serif realm names."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as nd

OUT = os.path.dirname(os.path.abspath(__file__))
code = open(os.path.join(OUT, 'draw.py')).read().split("Lb = np.asarray")[0]
ns = {}
exec(code, ns)
L, REALMS, base = ns['L'], ns['REALMS'], ns['base']
rng = np.random.RandomState(4)

S = 2
W, H = base.width * S, base.height * S
src = np.asarray(base.resize((W, H), Image.LANCZOS)).astype(np.float32)
Lb = np.asarray(Image.fromarray((L + 1).astype(np.uint8)).resize((W, H), Image.NEAREST)).astype(int) - 1
land = Lb >= 0

def fbm(scale, octaves=4):
    out = np.zeros((H, W)); amp = 1.0; tot = 0
    for o in range(octaves):
        out += amp * nd.gaussian_filter(rng.rand(H, W), scale / (2 ** o)); tot += amp; amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min())

paper = fbm(40)
fibre = fbm(2, 2)
# sea: muted grey-green wash, deeper water slightly darker, faint wave lines near coasts
dist_sea = nd.distance_transform_edt(~land)
sea = np.array([150, 162, 146], np.float32)
img = np.zeros((H, W, 3), np.float32)
deep = np.clip(dist_sea / 160.0, 0, 1)
img[:] = sea * (1.02 - 0.12 * deep[..., None]) * (0.93 + 0.12 * paper[..., None])
waves = (np.abs(((dist_sea % 14) - 7)) < 0.8) & (dist_sea < 40) & (dist_sea > 6)
img[waves] *= 0.94
# land: cream parchment with engraved relief from the source map
lum = src.mean(axis=2) / 255.0
gy, gx = np.gradient(nd.gaussian_filter(lum, 1.5))
relief = np.clip(1.0 + (gx + gy) * -8.0, 0.7, 1.15)
parch = np.array([232, 218, 184], np.float32) * (0.9 + 0.14 * paper[..., None]) * (0.96 + 0.06 * fibre[..., None])
img[land] = (parch * relief[..., None])[land]
# realms: solid muted colours, darker toward their borders
def muted(c):
    c = np.array(c, np.float32)
    g = c.mean()
    return (c * 0.72 + g * 0.28) * 0.92
for i, (name, ruler, col, _) in enumerate(REALMS):
    m = Lb == i
    if col is None or not m.any():
        continue
    inside = nd.distance_transform_edt(m)
    c = muted(col)
    k = 0.66 + 0.2 * np.exp(-inside / 10.0)
    dark = 1.0 - 0.18 * np.exp(-inside / 6.0)
    base_c = img[m]
    img[m] = (base_c * (1 - k[m][:, None]) + c * k[m][:, None]) * dark[m][:, None] * relief[m][:, None] ** 0.5
# ink: realm borders and coasts
edge = np.zeros((H, W), bool)
for dx, dy in ((1, 0), (0, 1)):
    sh = np.roll(np.roll(Lb, dx, 1), dy, 0)
    edge |= (Lb != sh) & (Lb >= 0) & (sh >= 0)
img[nd.binary_dilation(edge, iterations=1)] = (58, 44, 34)
coast = land & nd.binary_dilation(~land, iterations=1)
img[nd.binary_dilation(coast, iterations=1)] = (70, 56, 42)

# torn parchment sheet on a dark wooden table
margin = 70
yy, xx = np.mgrid[0:H, 0:W]
edge_noise = fbm(14, 3)
dist_edge = np.minimum.reduce([xx - margin, W - margin - xx, yy - margin, H - margin - yy]).astype(np.float32)
torn = dist_edge + (edge_noise - 0.5) * 60 + (fibre - 0.5) * 10
sheet = torn > 0
wood = np.zeros((H, W, 3), np.float32)
grain = np.sin(yy / 3.0 + fbm(30, 3) * 18) * 0.5 + 0.5
plank = ((yy // 140) % 2) * 0.06
wood[:] = np.array([62, 44, 32]) * (0.75 + 0.25 * grain[..., None] + plank[..., None])
img[~sheet] = wood[~sheet]
burn = sheet & (torn < 14)
img[burn] *= (0.55 + 0.45 * (torn[burn] / 14.0))[:, None]
vign = np.clip(1.1 - ((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / (W * W * 0.7), 0.6, 1.0)
img *= vign[..., None]

out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
d = ImageDraw.Draw(out)
def F(sz, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    try:
        return ImageFont.truetype(p, sz)
    except OSError:
        return ImageFont.load_default()
POS = {}
for i, (name, ruler, col, _) in enumerate(REALMS):
    if col is None:
        continue
    lab, n = nd.label(Lb == i)
    if not n:
        continue
    sizes = nd.sum(np.ones_like(lab), lab, range(1, n + 1))
    big = lab == (np.argmax(sizes) + 1)
    dt = nd.distance_transform_edt(big)
    cy, cx = np.unravel_index(np.argmax(dt), dt.shape)
    title = name.replace("The ", "").replace("Principality of ", "").upper()
    size = int(np.clip(np.sqrt(sizes.max()) / 6.5, 24, 64))
    f = F(size)
    w = d.textlength(title, font=f)
    while w > dt.max() * 3.6 and size > 22:
        size -= 2; f = F(size); w = d.textlength(title, font=f)
    d.text((cx - w / 2, cy - size * 0.6), title, font=f, fill=(40, 30, 22, 235))
    POS[name] = (float(cx) / W, float(cy) / H)
# compass rose and the council seat
cxr, cyr, r = 240, 250, 80
d.ellipse([cxr - r, cyr - r, cxr + r, cyr + r], outline=(120, 90, 60, 255), width=3, fill=(214, 196, 150, 200))
for k in range(16):
    a = np.radians(k * 22.5)
    d.line([(cxr, cyr), (cxr + np.sin(a) * r * 1.6, cyr - np.cos(a) * r * 1.6)], fill=(120, 90, 60, 120), width=1)
for ang, ln in ((0, 1.0), (90, 0.7), (180, 0.7), (270, 0.7)):
    a = np.radians(ang - 90)
    tip = (cxr + np.cos(a) * r * ln, cyr + np.sin(a) * r * ln)
    l_ = (cxr + np.cos(a + 2.7) * 14, cyr + np.sin(a + 2.7) * 14)
    r_ = (cxr + np.cos(a - 2.7) * 14, cyr + np.sin(a - 2.7) * 14)
    d.polygon([tip, l_, (cxr, cyr)], fill=(90, 62, 40, 255)); d.polygon([tip, r_, (cxr, cyr)], fill=(200, 150, 70, 255))
d.text((cxr - 9, cyr - r - 36), "N", font=F(26), fill=(70, 50, 34, 255))
vx, vy = int(728 * S), int(395 * S)
d.regular_polygon((vx, vy, 13), 5, rotation=0, fill=(214, 170, 60, 255), outline=(58, 44, 34, 255))
out = out.convert('RGB')
out.save(os.path.join(OUT, 'Realms_Campaign_Map.png'))
out.resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, 'realms_campaign_1024.png'))
import json
json.dump(POS, open(os.path.join(OUT, 'realm_pos.json'), 'w'), indent=1)
print('ok', out.size)
