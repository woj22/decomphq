"""Draw the realms of the Empire over the Elosia overhead map: territories follow the land (water excluded),
borders where realms meet, and a label for each realm with its ruler."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.spatial import cKDTree
from scipy import ndimage as nd

SRC = '/root/.claude/uploads/a03d530b-045f-5689-a491-bd153da4f61e/193c52c8-image.png'
base = Image.open(SRC).convert('RGB')
S = 2
img = base.resize((base.width * S, base.height * S), Image.LANCZOS)
a = np.asarray(base).astype(int)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
water = (B > R + 25) & (B > G + 5)
water = nd.binary_opening(water, iterations=1)
land = ~water
land = nd.binary_opening(land, iterations=1)

# realm: (name, ruler, colour, seed points in map-image pixels)
REALMS = [
    ("The Imperial Heartland", "the Emperor Aurex IV - seat of the Imperial Council", (190, 40, 50), [(710, 410), (660, 450), (760, 420), (650, 530), (720, 540)]),
    ("Velithra", "Queen Ilsaveth (Veyari)", (70, 150, 220), [(420, 230), (520, 200), (600, 220), (650, 280), (470, 300), (560, 300), (380, 260)]),
    ("Karst Odun", "King Oduvar (Othari)", (150, 150, 165), [(200, 300), (150, 420), (280, 400), (320, 330), (250, 520), (120, 520), (300, 250), (90, 380)]),
    ("Khar-Dumeth", "King Thrask (Kharad)", (230, 100, 30), [(430, 420), (500, 450), (380, 470), (540, 400), (460, 520), (520, 520), (600, 420)]),
    ("Tor-Ilun", "Queen Vashka (Kharad)", (200, 160, 40), [(700, 620), (640, 600), (780, 630), (640, 700), (700, 680)]),
    ("Lucerna", "King Marcellan Dorr", (120, 60, 160), [(300, 640), (380, 650), (250, 600), (470, 600), (470, 680), (420, 720), (520, 620)]),
    ("Meridia", "Governor Halvana (Imperial province)", (40, 160, 140), [(500, 790), (780, 790), (720, 820), (450, 780), (620, 800)]),
    ("Principality of Vaccaria", "Prince of Vaccaria (you)", (60, 180, 60), [(200, 700), (230, 760), (180, 790), (260, 720), (150, 690)]),
    (None, "Unclaimed", None, [(330, 150), (400, 145), (450, 140), (760, 150), (820, 250), (870, 190), (700, 80), (880, 300), (850, 480), (60, 640), (90, 740), (880, 650)]),
]
pts, lab = [], []
for i, (_, _, _, seeds) in enumerate(REALMS):
    for s in seeds:
        pts.append(s); lab.append(i)
ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
_, nn = cKDTree(np.array(pts)).query(np.c_[xs.ravel(), ys.ravel()])
L = np.array(lab)[nn].reshape(a.shape[:2])
L[~land] = -1
# smooth the territory edges a little
for i in range(len(REALMS)):
    m = nd.binary_closing(L == i, iterations=2) & land
    L[m & (L == -1)] = i

Lb = np.asarray(Image.fromarray((L + 1).astype(np.uint8)).resize(img.size, Image.NEAREST)).astype(int) - 1
over = np.zeros((img.size[1], img.size[0], 4), np.uint8)
for i, (name, ruler, col, _) in enumerate(REALMS):
    if col is None:
        continue
    m = Lb == i
    over[m] = col + (92,)
# borders: where neighbouring land pixels belong to different realms, and a darker coastal rim per realm
edge = np.zeros(Lb.shape, bool)
for dx, dy in ((1, 0), (0, 1)):
    sh = np.roll(np.roll(Lb, dx, 1), dy, 0)
    edge |= (Lb != sh) & (Lb >= 0) & (sh >= 0)
edge = nd.binary_dilation(edge, iterations=2)
over[edge] = (40, 22, 18, 230)
coast = (Lb >= 0) & nd.binary_dilation(Lb < 0, iterations=1)
inner = (nd.binary_dilation(edge | coast, iterations=5) & ~edge & (Lb >= 0))
for i, (name, ruler, col, _) in enumerate(REALMS):
    if col is None:
        continue
    m = inner & (Lb == i)
    over[m] = col + (200,)
out = Image.alpha_composite(img.convert('RGBA'), Image.fromarray(over))

d = ImageDraw.Draw(out)
def font(sz, bold=False):
    for f in (["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"] if bold else ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]) + ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()
F1, F2 = font(26, True), font(17)
# label each realm at the land pixel nearest the centroid of its largest piece
for i, (name, ruler, col, _) in enumerate(REALMS):
    if col is None:
        continue
    lab_, n = nd.label(Lb == i)
    if n == 0:
        continue
    sizes = nd.sum(np.ones_like(lab_), lab_, range(1, n + 1))
    big = lab_ == (np.argmax(sizes) + 1)
    cy, cx = nd.center_of_mass(big)
    dist = nd.distance_transform_edt(big)
    yy, xx = np.unravel_index(np.argmax(dist * (1.0 / (1.0 + np.hypot(np.arange(big.shape[0])[:, None] - cy, np.arange(big.shape[1])[None, :] - cx) / 80.0))), big.shape)
    w1 = d.textlength(name, font=F1); w2 = d.textlength(ruler, font=F2)
    w = max(w1, w2) + 28
    x0, y0 = xx - w / 2, yy - 34
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 66], 8, fill=(248, 238, 214, 225), outline=col + (255,), width=3)
    d.text((xx - w1 / 2, y0 + 6), name, font=F1, fill=(50, 30, 20, 255))
    d.text((xx - w2 / 2, y0 + 38), ruler, font=F2, fill=(90, 60, 40, 255))
# title cartouche
T = "THE REALMS OF THE EMPIRE"
tw = d.textlength(T, font=font(34, True))
d.rounded_rectangle([out.width / 2 - tw / 2 - 24, 18, out.width / 2 + tw / 2 + 24, 76], 10, fill=(248, 238, 214, 235), outline=(150, 110, 40, 255), width=3)
d.text((out.width / 2 - tw / 2, 28), T, font=font(34, True), fill=(60, 35, 20, 255))
# legend
items = [(n, r, c) for n, r, c, _ in REALMS if c is not None]
lx, ly = 24, 96
d.rounded_rectangle([lx, ly, lx + 540, ly + 60 + 34 * len(items)], 10, fill=(248, 238, 214, 235), outline=(150, 110, 40, 255), width=3)
d.text((lx + 18, ly + 12), "Realms and rulers", font=font(22, True), fill=(60, 35, 20, 255))
for k, (n, r, c) in enumerate(items):
    yy = ly + 50 + k * 34
    d.rounded_rectangle([lx + 18, yy, lx + 46, yy + 24], 4, fill=c + (255,), outline=(60, 35, 20, 255))
    d.text((lx + 58, yy + 1), n, font=font(17, True), fill=(50, 30, 20, 255))
    d.text((lx + 58 + d.textlength(n, font=font(17, True)) + 8, yy + 3), "- " + r.split(" (")[0].split(" - ")[0], font=font(15), fill=(100, 70, 45, 255))
out.convert('RGB').save('/tmp/claude-0/-home-user-decomphq/a03d530b-045f-5689-a491-bd153da4f61e/scratchpad/realms/Elosia_Realms.png')
print('ok', out.size)
