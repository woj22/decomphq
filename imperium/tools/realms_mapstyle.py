"""The realms map in vanilla Minecraft map style: only map-palette colours (each in its 4 map shades), sized for a
4x4 wall of in-game maps (512x512 map pixels = 16 tiles of 128x128)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as nd
import importlib.util, sys, os
spec = importlib.util.spec_from_file_location('draw', os.path.join(os.path.dirname(__file__), 'draw.py'))
SRC = '/root/.claude/uploads/a03d530b-045f-5689-a491-bd153da4f61e/193c52c8-image.png'
OUT = os.path.dirname(os.path.abspath(__file__))

# reuse the realm layout (territory labels) from draw.py without its rendering
code = open(os.path.join(OUT, 'draw.py')).read().split("Lb = np.asarray")[0]
ns = {}
exec(code, ns)
L, REALMS, base = ns['L'], ns['REALMS'], ns['base']

N = 512
Lm = np.asarray(Image.fromarray((L + 1).astype(np.uint8)).resize((N, N), Image.NEAREST)).astype(int) - 1
src = np.asarray(base.resize((N, N), Image.LANCZOS)).astype(float)
lum = src.mean(axis=2)

SHADES = (180 / 255, 220 / 255, 1.0, 135 / 255)
def sh(c, k):
    return tuple(int(v * SHADES[k]) for v in c)

WATER = (64, 64, 255)
MAPCOL = {  # realm -> map base colour
    "The Imperial Heartland": (153, 51, 51), "Velithra": (102, 153, 216), "Karst Odun": (199, 199, 199), "Khar-Dumeth": (216, 127, 51),
    "Tor-Ilun": (250, 238, 77), "Lucerna": (127, 63, 178), "Meridia": (76, 127, 153), "Principality of Vaccaria": (127, 204, 25),
}
TERRAIN = [(127, 178, 56), (0, 124, 0), (247, 233, 163), (255, 255, 255), (112, 112, 112), (151, 109, 77), (216, 127, 51), (160, 160, 255)]

img = np.zeros((N, N, 3), np.uint8)
# water: depth from distance to land, with the vanilla map's diagonal dither
dist = nd.distance_transform_edt(Lm < 0 if False else ~(nd.binary_dilation(lum > 0, iterations=0) & (Lm >= 0) | (Lm >= 0)))
yy, xx = np.mgrid[0:N, 0:N]
k_w = np.where(dist < 4, 2, np.where(dist < 12, 1, 0))
k_w = np.where((dist >= 12) & (((xx + yy) % 2) == 0) & (dist < 20), 1, k_w)
for k in range(3):
    img[(Lm < 0) & (k_w == k)] = sh(WATER, k)
# land: relief shading from the source image's brightness gradient (light from the north-west)
gy, gx = np.gradient(nd.gaussian_filter(lum, 1.0))
relief = -(gx + gy)
k_l = np.where(relief > 2.5, 2, np.where(relief < -2.5, 0, 1))
for i, (name, ruler, col, _) in enumerate(REALMS):
    m = Lm == i
    if not m.any():
        continue
    if col is None:      # unclaimed land keeps natural map colours
        sub = src[m]
        pal = np.array(TERRAIN, float)
        idx = np.argmin(((sub[:, None, :] - pal[None]) ** 2).sum(-1), axis=1)
        cols = np.array([[sh(TERRAIN[j], k) for k in range(4)] for j in range(len(TERRAIN))], np.uint8)
        img[m] = cols[idx, k_l[m]]
    else:
        c = MAPCOL[name]
        for k in range(3):
            img[m & (k_l == k)] = sh(c, k)
# borders between realms and along every coast, in the darkest shade
edge = np.zeros((N, N), bool)
for dx, dy in ((1, 0), (0, 1)):
    sh2 = np.roll(np.roll(Lm, dx, 1), dy, 0)
    edge |= (Lm != sh2) & (Lm >= 0) & (sh2 >= 0)
for i, (name, ruler, col, _) in enumerate(REALMS):
    if col is None:
        continue
    m = (Lm == i)
    img[m & edge] = (25, 25, 25)
    coast = m & nd.binary_dilation(Lm < 0, iterations=1)
    img[coast] = sh(MAPCOL[name], 3)

im = Image.fromarray(img)
d = ImageDraw.Draw(im)
try:
    F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
except OSError:
    F = ImageFont.load_default()
SHORT = {"The Imperial Heartland": "IMPERIAL HEARTLAND", "Principality of Vaccaria": "VACCARIA"}
for i, (name, ruler, col, _) in enumerate(REALMS):
    if col is None:
        continue
    lab, n = nd.label(Lm == i)
    if not n:
        continue
    sizes = nd.sum(np.ones_like(lab), lab, range(1, n + 1))
    big = lab == (np.argmax(sizes) + 1)
    dt = nd.distance_transform_edt(big)
    cy, cx = np.unravel_index(np.argmax(dt), dt.shape)
    t = SHORT.get(name, name.upper())
    w = d.textlength(t, font=F)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        d.text((cx - w / 2 + ox, cy - 6 + oy), t, font=F, fill=sh(MAPCOL[name], 3))
    d.text((cx - w / 2, cy - 6), t, font=F, fill=(255, 252, 245))
# the council seat: a gold star on the volcano
vx, vy = int(728 * N / 936), int(390 * N / 935)
for ddx, ddy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
    im.putpixel((vx + ddx, vy + ddy), (250, 238, 77))
im.save(os.path.join(OUT, 'realms_map_512.png'))
im.resize((N * 4, N * 4), Image.NEAREST).save(os.path.join(OUT, 'Realms_MapStyle_preview.png'))
os.makedirs(os.path.join(OUT, 'tiles'), exist_ok=True)
for r in range(4):
    for c in range(4):
        im.crop((c * 128, r * 128, c * 128 + 128, r * 128 + 128)).save(os.path.join(OUT, 'tiles', 'map_r%d_c%d.png' % (r, c)))
print('ok')
