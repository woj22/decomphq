import sys; sys.path.insert(0,'.')
from post import *
import numpy as np, glob
tag = sys.argv[1]; ink = (13, 11, 18)
R = lambda n: Image.open(f'raw_{tag}_{n}.png')
a = np.asarray(R('floor')); print('alpha uniq', np.unique(a[..., 3]))
Q = {}
for n in ('floor', 'floor_edge', 'wall_x_win', 'wall_x_plain', 'wall_y_win', 'wall_y_plain'): Q[n] = quantise(R(n))
for n in ('brazier', 'desk'): Q[n] = quantise(R(n), outline=ink)
for nm in ('clerk', 'soul', 'guard'):
    for f in range(4):
        for d in range(8):
            Q[f'{nm}_{f}_{d}'] = quantise(R(f'{nm}_{f}_{d}'), outline=(ink if nm != 'soul' else (106, 84, 132)))
for k, v in Q.items(): v.save(f'q_{tag}_{k}.png')
# sprite sheet: 8 dirs (cols) x 4 frames (rows)
for nm in ('clerk', 'soul', 'guard'):
    sh = Image.new('RGBA', (32*8, 56*4))
    for f in range(4):
        for d in range(8): sh.alpha_composite(Q[f'{nm}_{f}_{d}'], (d*32, f*56))
    sh.save(f'sheet_{tag}_{nm}.png')
sheets = Image.new('RGBA', (256, 56*3), (60, 50, 80, 255))
for i, nm in enumerate(('clerk', 'soul', 'guard')): sheets.alpha_composite(Image.open(f'sheet_{tag}_{nm}.png').crop((0, 0, 256, 56)), (0, i*56))
kit = Image.new('RGBA', (64*5+32+64, 128), (60, 50, 80, 255)); x = 0
for n in ('wall_x_win', 'wall_x_plain', 'wall_y_win', 'wall_y_plain', 'floor', 'brazier', 'desk'):
    kit.alpha_composite(Q[n], (x, 128-Q[n].height)); x += Q[n].width if n != 'floor' else 64
c = Image.new('RGBA', (max(kit.width, 256), kit.height+sheets.height), (60, 50, 80, 255)); c.alpha_composite(kit); c.alpha_composite(sheets, (0, kit.height))
c.resize((c.width*4, c.height*4), Image.NEAREST).save(f'c_kit_{tag}.png')
# ---- composite room
N = 6; W, H = 480, 320; ox, oy = 48, 190
img = Image.new('RGBA', (W, H), (26, 23, 34, 255))
def pos(x, y): return ox + (x+y)*32, oy + (x-y)*16
items = []
for x in range(N):
    for y in range(N):
        items.append((x-y, 0, 'floor_edge' if (x == N-1 or y == 0) else 'floor', pos(x, y), (32, 16)))
        if y == N-1: items.append((x-y-0.5, 1, 'wall_x_win' if x % 2 == 1 else 'wall_x_plain', pos(x, y), (32, 112)))
        if x == 0: items.append((x-y-0.5, 1, 'wall_y_win' if y % 2 == 0 else 'wall_y_plain', pos(x, y), (32, 112)))
for (x, y, n, anc) in [(1, 4, 'brazier', (16, 40)), (5, 4, 'brazier', (16, 40)), (3, 3, 'desk', (32, 48)), (3, 4, 'clerk_0_0', (16, 48)),
                       (3, 2, 'soul_0_4', (16, 48)), (3.6, 1.4, 'soul_1_4', (16, 48)), (4.2, 0.8, 'soul_2_3', (16, 48)), (1.5, 1.5, 'clerk_1_1', (16, 48)),
                       (5, 1, 'guard_0_6', (16, 48)), (1, 3, 'guard_0_2', (16, 48)), (2.2, 0.6, 'clerk_2_7', (16, 48))]:
    items.append((x-y+0.1, 2, n, pos(x, y), anc))
soul_layer = []
for depth, lay, n, (px, py), (ax, ay) in sorted(items, key=lambda t: (t[1] != 0, t[0], t[1])):
    sp = Q[n]
    if lay == 2:
        sh = Image.new('RGBA', (W, H)); from PIL import ImageDraw
        ImageDraw.Draw(sh).ellipse((px-9, py-4, px+8, py+4), fill=(13, 11, 18, 110)); img.alpha_composite(sh)
    if n.startswith('soul'):
        arr = np.asarray(sp).copy(); arr[..., 3] = (arr[..., 3]*0.75).astype(np.uint8); sp = Image.fromarray(arr)
    img.alpha_composite(sp, (int(px-ax), int(py-ay)))
img.save(f'room_{tag}_flat.png')
# fake Godot lighting: multiply by cold ambient, add gold lights
arr = np.asarray(img).astype(float)[..., :3]
yy, xx = np.mgrid[0:H, 0:W]
light = np.zeros((H, W))
def blob(cx, cy, rx, ry, k): 
    global light; d = ((xx-cx)/rx)**2 + ((yy-cy)/ry)**2; light = np.maximum(light, k*np.clip(1-d, 0, 1)**1.5)
for x in range(N):
    if x % 2 == 1: px, py = pos(x, N-1.9); blob(px, py, 60, 34, 0.9)
for y in range(N):
    if y % 2 == 0: px, py = pos(0.9, y); blob(px, py, 60, 34, 0.8)
for (x, y) in ((1, 4), (5, 4)): px, py = pos(x, y); blob(px, py-4, 80, 46, 1.0)
light = np.floor(light*5)/5          # banded light = pixel-art friendly
amb = np.array([0.62, 0.58, 0.80]); gold = np.array([1.25, 1.02, 0.62])
emis = np.zeros((H, W), bool)
for e in ((246,214,122),(255,243,196),(232,85,43)): emis |= (arr == np.array(e)).all(-1)
out = arr*amb[None, None] + arr*gold[None, None]*light[..., None]*1.1 + np.array([40, 26, 6])[None, None]*light[..., None]
out[emis] = arr[emis]
out = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert('RGBA')
q = quantise(out)
q.resize((W*3, H*3), Image.NEAREST).save(f'room_{tag}_lit.png')
img.resize((W*3, H*3), Image.NEAREST).save(f'room_{tag}_flat3.png')
