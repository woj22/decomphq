"""Turn the painted overhead city map (reference/city_map.png) into a coarse land-use grid for the game.

Each 4x4-pixel cell (~12 m; the map's scale bar gives ~3.03 m per pixel) gets one class:
  W water, T trees, F fields/countryside, R dense roofs (buildings), P paving (streets, plazas), G garden
Output: web/data/citymap.json  {w, h, cell_m, rows: [...strings...]}  and a debug image renders/citymap_classes.png
"""
import json
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
im = Image.open(os.path.join(ROOT, "reference", "city_map.png")).convert("RGB")
a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
mx, mn = a.max(-1), a.min(-1)
S = (mx - mn) / np.maximum(mx, 1)
V = mx

water = (B > R + 4) & (B > G - 2) & (V < 200)
tree = (G > R * 0.92) & (G > B * 1.15) & (V < 140)
roof = (R > G * 1.45) & (R > 120) & (S > 0.35)
light = (V > 175) & (S < 0.42)
paving = (S < 0.36) & (V > 105) & (V <= 175) & ~water
field = (R > G * 1.15) & (G > B * 1.25) & (S > 0.38) & ~roof

C = 4
h, w = a.shape[0] // C, a.shape[1] // C
def frac(m):
    return m[:h * C, :w * C].reshape(h, C, w, C).mean((1, 3))
fw, ft, fr, fl, fp, ff = (frac(m) for m in (water, tree, roof, light, paving, field))
cls = np.full((h, w), "F")
built = fr + fl * 0.8
cls[(fp > 0.45) & (built < 0.35)] = "P"
cls[built >= 0.35] = "R"
cls[(ft > 0.35) & (built < 0.45)] = "T"
cls[fw > 0.45] = "W"
# inside the city wall the gaps between roofs are streets (S); outside, only strongly red areas are villas (V)
WALL = [(62, 505), (300, 330), (350, 265), (285, 150), (580, 95), (640, 75), (960, 75), (1100, 135), (1240, 235), (1380, 320),
        (1420, 470), (1445, 640), (1450, 770), (1405, 850), (1200, 940), (950, 835), (745, 835), (430, 770), (280, 690), (95, 600)]
from PIL import ImageDraw
mask = Image.new("L", (w, h), 0)
ImageDraw.Draw(mask).polygon([(x / C, y / C) for x, y in WALL], fill=1)
inside = np.asarray(mask).astype(bool)
strong = frac((R > G * 1.75) & (R > 130))
cls[inside & (cls == "F")] = "S"
cls[inside & (cls == "P")] = "S"
cls[~inside & (cls == "R") & (strong < 0.35)] = "F"
cls[~inside & (cls == "R")] = "V"
# street orientation: structure tensor of the blurred roof mask, quantised to 10-degree steps (mod 180)
rb = np.asarray(Image.fromarray((fr * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
gy, gx = np.gradient(rb)
def blur(m, r):
    lo, hi = m.min(), m.max()
    im8 = Image.fromarray(((m - lo) / max(hi - lo, 1e-9) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im8).astype(np.float32) / 255 * (hi - lo) + lo
jxx, jyy, jxy = blur(gx * gx, 3), blur(gy * gy, 3), blur(gx * gy, 3)
ang = 0.5 * np.arctan2(2 * jxy, jxx - jyy)          # direction of strongest gradient (across the street)
q = np.round((ang % np.pi) / (np.pi / 18)).astype(int) % 18
orient = ["".join(chr(97 + v) for v in row) for row in q]
# the legend and scale bar are not terrain
cls[:300 // C, :245 // C] = "F"
cls[950 // C:, :370 // C] = "F"
os.makedirs(os.path.join(ROOT, "web", "data"), exist_ok=True)
json.dump({"w": w, "h": h, "cell_m": 3.03 * C, "px_m": 3.03, "rows": ["".join(r) for r in cls], "orient": orient, "wall": WALL},
          open(os.path.join(ROOT, "web", "data", "citymap.json"), "w"))
pal = {"S": (235, 215, 170), "V": (230, 120, 60), "W": (60, 110, 200), "T": (40, 110, 40), "F": (200, 180, 110), "R": (190, 60, 50), "P": (235, 225, 210), "G": (120, 200, 120)}
out = np.zeros((h, w, 3), np.uint8)
for k, c in pal.items():
    out[cls == k] = c
Image.fromarray(out).resize((w * 3, h * 3), Image.NEAREST).save(os.path.join(ROOT, "renders", "citymap_classes.png"))
print("grid", w, h, {k: int((cls == k).sum()) for k in pal})
