"""Snowbound: builds the train interior in Blender, bakes its lighting and exports glTF modules.

    python3 snowbound/tools/build_train.py [module ...] [--fast]

Modules (Godot coordinates, x across the train, y up, z along it; the locomotive is toward -z):
  compartment   one sleeper compartment, x -1.45..0.40, z 0..2.4 (instanced six times, z = 0, 2.4, ... 12.0)
  corridor      the corridor beside one compartment, x 0.40..1.45, z 0..2.4 (instanced six times)
  sleeper_front washroom wall + end door, z -1.6..0
  sleeper_rear  conductor's office, vestibule and gangway, z 14.4..17.6
  dining_bay    one dining bay (4-seat booth left, 2-seat right), z 0..2.4 (instanced at 17.6 + 2.4 i, i = 0..3)
  dining_end    bar, coal stove, armchairs and the locked baggage-car door, z 27.2..32.0

Every module is one mesh (several materials) with a baked lightmap on its second UV set: assets/train/<module>.glb,
assets/train/<module>_lm.png, plus <module>_lights.json describing the real-time lights the game adds (for
characters and highlights). Glass is a separate unbaked mesh.
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blib  # noqa: E402
from blib import area_light, box, cyl, mat, point_light, reset, sphere, torus, tube, world_sky  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'train')
os.makedirs(OUT, exist_ok=True)
FAST = '--fast' in sys.argv

W2 = 1.45            # half width
H = 2.15             # ceiling height
PART = 0.40          # corridor-side face of the partition (compartments are x < PART)
WARM = (1.0, 0.72, 0.46)
MOON = (0.42, 0.55, 0.85)

# metres per texture repeat, by material
UV_SCALE = {'Panel': 1.2, 'Trim': 0.9, 'Floorwood': 1.4, 'Velvet': 0.6, 'Damask': 0.7, 'Linen': 0.5, 'Leather': 0.6,
            'Runner': 0.9, 'Ceiling': 1.5, 'Tablecloth': 0.6, 'Carpet': 0.8}


def M():
    """Materials. Base colours approximate the game textures so bounce light picks up the right colour."""
    return {
        'Panel': mat('Panel', '#6e2e16', 0.35),
        'Trim': mat('Trim', '#2c130a', 0.3),
        'Floorwood': mat('Floorwood', '#2a150b', 0.45),
        'Velvet': mat('Velvet', '#5e0e1c', 0.9),
        'Damask': mat('Damask', '#561320', 0.85),
        'Linen': mat('Linen', '#e9e3d6', 0.9),
        'Tablecloth': mat('Tablecloth', '#ece6da', 0.85),
        'Leather': mat('Leather', '#4a2812', 0.55),
        'Runner': mat('Runner', '#58141e', 1.0),
        'Carpet': mat('Carpet', '#3c0e16', 1.0),
        'Ceiling': mat('Ceiling', '#e0d2b4', 0.8),
        'Brass': mat('Brass', '#b88c40', 0.3, 1.0),
        'Shade': mat('LampShade', '#f2dcb0', 0.8, emit='#ffc98a', strength=4.0),
        'Bulb': mat('LampGlass', '#fff2d8', 0.3, emit='#ffe2b8', strength=12.0),
        'Black': mat('Black', '#121214', 0.5),
        'Ceramic': mat('Ceramic', '#f2efe8', 0.2),
        'Silver': mat('Silver', '#c8c8cc', 0.25, 1.0),
        'Picture': mat('Picture', '#8c7c62', 0.9),
        'Paper': mat('Paper', '#e6dcc4', 0.9),
        'Marble': mat('Marble', '#d6d0c6', 0.25),
        'Iron': mat('Iron', '#1a1a1d', 0.55, 0.6),
        'Coal': mat('Coal', '#0c0c0d', 0.7),
        'Fire': mat('StoveGlow', '#ff7a2a', 0.5, emit='#ff6a1e', strength=10.0),
        'Petal': mat('Petal', '#eee6d6', 0.6),
        'Leaf': mat('Leaf', '#3e5a2a', 0.6),
        'Bellows': mat('Bellows', '#161618', 0.9),
        'Glass': mat('Glass', '#b8d0e8', 0.05, alpha=0.25),
        'Bottle': mat('BottleGlass', '#2e5a2a', 0.1, alpha=0.6),
        'Amber': mat('AmberGlass', '#8a4a10', 0.1, alpha=0.6),
    }


# ------------------------------------------------------------------ building blocks
def framed_uv(o, w, h):
    """0..1 UVs across a flat picture lying in a z-facing plane."""
    me = o.data
    uv = me.uv_layers.new(name='UVMap')
    for li, loop in enumerate(me.loops):
        co = me.vertices[loop.vertex_index].co
        uv.data[li].uv = (0.5 - co.x / w, co.z / h + 0.5)
    return o


def runner(name, width, length, centre, m, repeat=0.9):
    """Carpet runner whose texture spans exactly its width (border on both edges) and repeats along its length."""
    o = box(name, (width, 0.008, length), centre, m['Runner'])
    me = o.data
    uv = me.uv_layers.new(name='UVMap')
    for li, loop in enumerate(me.loops):
        co = me.vertices[loop.vertex_index].co   # local: x across, -y along (Godot z)
        uv.data[li].uv = (co.x / width + 0.5, -co.y / repeat)
    return o

def panelled(P, m, axis, pos, a0, a1, y0, y1, inward, thick=0.05, panel_w=0.62, rail=0.85, cap=True):
    """A panelled wood wall: a slab in the plane axis = pos ('x' or 'z'), running a0..a1 along the other horizontal
    axis and y0..y1, with a dado rail and raised panel frames on the inward face (inward = +1 or -1)."""
    def put(name, size_along, size_y, depth, along, y, off, material, bevel=0.0):
        d = pos + inward * off
        if axis == 'x':
            P(box(name, (depth, size_y, size_along), (d, y, along), material, bevel=bevel))
        else:
            P(box(name, (size_along, size_y, depth), (along, y, d), material, bevel=bevel))
    L = a1 - a0
    put('slab', L, y1 - y0, thick, (a0 + a1) / 2, (y0 + y1) / 2, 0, m['Panel'])
    if rail and y0 < rail < y1:
        put('dado', L, 0.05, 0.03, (a0 + a1) / 2, rail, thick / 2 + 0.012, m['Trim'], bevel=0.008)
    r = rail if rail else y1
    for band0, band1 in ((y0 + 0.08, min(r, y1) - 0.07), (min(r, y1) + 0.08, y1 - 0.1)):
        if band1 - band0 < 0.25:
            continue
        n = max(1, round(L / panel_w))
        w = L / n
        for i in range(n):
            c = a0 + w * (i + 0.5)
            bw = w - 0.12
            yc, bh = (band0 + band1) / 2, band1 - band0
            for (sa, sy, da, dy) in ((bw + 0.04, 0.03, 0, bh / 2), (bw + 0.04, 0.03, 0, -bh / 2), (0.03, bh, bw / 2, 0), (0.03, bh, -bw / 2, 0)):
                put('moulding', sa, sy, 0.018, c + da, yc + dy, thick / 2 + 0.009, m['Trim'], bevel=0.006)
    if cap:
        put('cornice', L, 0.06, 0.05, (a0 + a1) / 2, y1 - 0.03, thick / 2 + 0.02, m['Trim'], bevel=0.012)


def window_wall(P, G, m, x, inward, z0, z1, wz0, wz1, wy0=0.88, wy1=1.74, curtains=True):
    """Outer wall at x with one window opening (wz0..wz1, wy0..wy1): panelling below, frame, sill, glass, curtains."""
    panelled(P, m, 'x', x, z0, z1, 0.0, wy0, inward, rail=None, cap=False)
    P(box('above', (0.05, H - wy1, z1 - z0), (x, (wy1 + H) / 2, (z0 + z1) / 2), m['Panel']))
    for a, b in ((z0, wz0), (wz1, z1)):
        if b - a > 0.01:
            P(box('pier', (0.05, wy1 - wy0, b - a), (x, (wy0 + wy1) / 2, (a + b) / 2), m['Panel']))
    wc, ww, wh = (wz0 + wz1) / 2, wz1 - wz0, wy1 - wy0
    fx = x + inward * 0.035
    for dz in (-1, 1):
        P(box('jamb', (0.07, wh + 0.08, 0.06), (fx, (wy0 + wy1) / 2, wc + dz * (ww / 2 + 0.01)), m['Trim'], bevel=0.015))
    P(box('head', (0.07, 0.07, ww + 0.1), (fx, wy1 + 0.01, wc), m['Trim'], bevel=0.015))
    P(box('sill', (0.16, 0.04, ww + 0.16), (x + inward * 0.07, wy0 - 0.01, wc), m['Trim'], bevel=0.012))
    P(box('glazing_bar', (0.03, 0.035, ww), (fx, wy1 - 0.22, wc), m['Trim'], bevel=0.008))
    G.append(box('pane', (0.012, wh, ww), (x - inward * 0.005, (wy0 + wy1) / 2, wc), m['Glass']))
    if curtains:
        for dz in (-1, 1):
            edge = wc + dz * (ww / 2 + 0.16)       # the curtain hangs from here and is tied back toward it
            top, bot = wy1 + 0.12, wy0 - 0.08
            tie_y = wy0 + 0.42
            P(drape('curtain', x + inward * 0.11, inward, edge, -dz, top, bot, tie_y, 0.34, m['Velvet']))
            P(sphere('tassel_knot', 0.022, (x + inward * 0.16, tie_y, edge - dz * 0.06), m['Brass'], segs=10, rings=6))
            P(cyl('tassel', 0.012, 0.03, 0.12, (x + inward * 0.16, tie_y - 0.08, edge - dz * 0.06), m['Brass'], segs=10))
        val = blib.subsurf(box('valance', (0.08, 0.17, ww + 0.5), (x + inward * 0.1, wy1 + 0.15, wc), m['Velvet'], bevel=0.03, seg=1), 1)
        P(val)


def drape(name, x, inward, edge_z, toward, top, bot, tie_y, width, material, cols=20, rows=18):
    """A velvet curtain: a pleated sheet hanging from `top`, gathered to a narrow bunch at the tie-back (tie_y) near
    edge_z, flaring a little below it. `toward` is the direction (+1/-1 in z) the open curtain would spread."""
    import bmesh
    bm = bmesh.new()
    grid = []
    for r in range(rows + 1):
        t = r / rows
        y = top - t * (top - bot)
        tie = math.exp(-((y - tie_y) / 0.12) ** 2)
        below = max(0.0, (tie_y - y) / max(0.01, tie_y - bot))
        w = width * (1.0 - 0.72 * tie) * (1.0 if y > tie_y else (0.35 + 0.45 * below))
        if y > tie_y:
            w = width * (1.0 - 0.72 * tie) * (1.0 - 0.45 * (1 - (y - tie_y) / max(0.01, top - tie_y)) ** 2)
        row = []
        for c in range(cols + 1):
            u = c / cols
            pleat = math.sin(u * math.pi * 7) * (0.022 + 0.012 * tie) * (0.6 + 0.4 * w / width)
            bulge = 0.05 * tie * math.sin(u * math.pi)
            row.append(bm.verts.new(blib.g(x + inward * (pleat + bulge), y, edge_z + toward * u * w)))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for c in range(cols):
            bm.faces.new((a[c], a[c + 1], b[c + 1], b[c]))
    o = blib._obj(name, bm, material, smooth=True)
    return blib.solidify(o, 0.012)


def sconce(P, m, wall_x, inward, y, z):
    """Wall lamp: brass back plate and arm, pleated shade. Returns the bulb position."""
    P(cyl('plate', 0.045, 0.045, 0.02, (wall_x + inward * 0.03, y, z), m['Brass'], rot=(0, 0, 90), segs=16))
    bx = wall_x + inward * 0.18
    P(tube('arm', [(wall_x + inward * 0.04, y, z), (wall_x + inward * 0.12, y + 0.04, z), (bx, y + 0.07, z)], 0.01, m['Brass'], segs=8))
    P(cyl('shade', 0.09, 0.055, 0.15, (bx, y + 0.15, z), m['Shade'], segs=20, cap=False))
    P(sphere('bulb', 0.025, (bx, y + 0.13, z), m['Bulb'], segs=10, rings=6))
    return (bx, y + 0.13, z)


def dome(P, m, x, z, h=H):
    P(cyl('dome_rim', 0.17, 0.17, 0.025, (x, h - 0.02, z), m['Brass'], segs=24))
    P(sphere('dome', 0.15, (x, h - 0.04, z), m['Bulb'], scale=(1, 0.45, 1), segs=24, rings=10))
    return (x, h - 0.12, z)


def flowers(P, m, x, y, z):
    P(cyl('vase', 0.03, 0.045, 0.14, (x, y + 0.07, z), m['Silver'], segs=16))
    rng = random.Random(int(z * 100))
    for i in range(7):
        a = i * 2.4
        tip = (x + math.cos(a) * 0.06, y + 0.28 + rng.random() * 0.08, z + math.sin(a) * 0.06)
        P(tube('stem', [(x, y + 0.13, z), tip], 0.003, m['Leaf'], segs=4, cap=False))
        for k in range(5):
            b = k * math.tau / 5
            P(sphere('petal', 0.013, (tip[0] + math.cos(b) * 0.012, tip[1], tip[2] + math.sin(b) * 0.012), m['Petal'], scale=(1, 0.4, 1), segs=6, rings=4))


def suitcase(P, m, x, y, z, w, h, d, mat_):
    P(box('case', (d, h, w), (x, y + h / 2, z), mat_, bevel=0.018))
    for dz in (-w / 3, w / 3):
        P(box('strap', (d + 0.006, h + 0.006, 0.025), (x, y + h / 2, z + dz), m['Trim']))
    for cz in (-w / 2.6, w / 2.6):
        P(box('corner', (d + 0.01, 0.03, 0.03), (x, y + h - 0.015, z + cz), m['Brass']))
    P(tube('handle', [(x, y + h, z - 0.06), (x, y + h + 0.035, z), (x, y + h, z + 0.06)], 0.009, m['Leather'], segs=6))


def luggage_net(P, m, x0, x1, y, z0, z1):
    """Brass-railed shelf with a net, like the one over the door in the reference."""
    for x in (x0, x1):
        P(cyl('rail', 0.012, 0.012, z1 - z0, (x, y, (z0 + z1) / 2), m['Brass'], rot=(90, 0, 0), segs=10))
    for z in (z0 + 0.03, z1 - 0.03):
        P(tube('bracket', [(x1, y, z), (x1 + (0.05 if x1 > x0 else -0.05), y + 0.12, z)], 0.01, m['Brass'], segs=6))
    n = int((z1 - z0) / 0.07)
    for i in range(n + 1):  # diagonal net strands both ways
        za = z0 + i * (z1 - z0) / n
        zb = min(z1, za + 0.25)
        P(tube('net', [(x0, y - 0.005, za), ((x0 + x1) / 2, y - 0.03, (za + zb) / 2), (x1, y - 0.005, zb)], 0.0035, m['Paper'], segs=4, cap=False))
        zc = max(z0, za - 0.25)
        P(tube('net', [(x0, y - 0.005, za), ((x0 + x1) / 2, y - 0.03, (za + zc) / 2), (x1, y - 0.005, zc)], 0.0035, m['Paper'], segs=4, cap=False))


# ------------------------------------------------------------------ modules
def compartment():
    """One sleeper compartment (x -1.45..0.40, z 0..2.4). The door opening is in the partition at z 0.2..0.95."""
    m = M()
    P, G, lights = [], [], []
    p = P.append
    # floor, ceiling, walls
    p(box('floor', (W2 + PART, 0.04, 2.4), ((-W2 + PART) / 2, -0.02, 1.2), m['Carpet']))
    p(box('ceiling', (W2 + PART, 0.05, 2.4), ((-W2 + PART) / 2, H + 0.025, 1.2), m['Ceiling']))
    for (xa, xb, s) in ((-W2, -W2 + 0.18, 1), (PART - 0.14, PART, -1)):
        p(box('cove', (xb - xa, 0.08, 2.4), ((xa + xb) / 2, H - 0.04, 1.2), m['Trim'], bevel=0.02))
    window_wall(p, G, m, -W2 + 0.025, 1, 0.0, 2.4, 0.5, 1.75)
    panelled(p, m, 'z', 0.025, -W2, PART, 0, H, 1)          # front end wall
    panelled(p, m, 'z', 2.375, -W2, PART, 0, H, -1)         # back end wall (bed wall)
    # partition with the door opening (z 0.2..0.95)
    px = PART - 0.025
    panelled(p, m, 'x', px, 0.95, 2.4, 0, H, -1)
    p(box('part_a', (0.05, H, 0.2), (px, H / 2, 0.1), m['Panel']))
    p(box('part_top', (0.05, H - 2.0, 0.75), (px, (2.0 + H) / 2, 0.575), m['Panel']))
    for zz in (0.2, 0.95):
        p(box('door_jamb', (0.09, 2.0, 0.05), (px - 0.01, 1.0, zz), m['Trim'], bevel=0.012))
    p(box('door_head', (0.09, 0.06, 0.8), (px - 0.01, 2.02, 0.575), m['Trim'], bevel=0.012))

    # bed along the back wall, pillow at the window end
    bz0, bz1 = 1.62, 2.34
    bx0, bx1 = -W2 + 0.06, PART - 0.07
    bc, bw = (bz0 + bz1) / 2, bz1 - bz0
    p(box('bed_base', (bx1 - bx0, 0.36, bw), ((bx0 + bx1) / 2, 0.18, bc), m['Trim'], bevel=0.02))
    for i in range(2):
        cx = bx0 + (bx1 - bx0) * (0.27 + 0.46 * i)
        p(box('drawer', ((bx1 - bx0) * 0.4, 0.2, 0.02), (cx, 0.18, bz0 - 0.005), m['Panel'], bevel=0.008))
        p(cyl('pull', 0.012, 0.012, 0.02, (cx, 0.2, bz0 - 0.02), m['Brass'], rot=(90, 0, 0), segs=10))
    p(blib.subsurf(box('mattress', (bx1 - bx0 - 0.02, 0.16, bw - 0.02), ((bx0 + bx1) / 2, 0.44, bc), m['Linen'], bevel=0.05, seg=1), 1))
    spread = box('bedspread', (bx1 - bx0 - 0.42, 0.04, bw + 0.04), ((bx0 + bx1) / 2 + 0.21, 0.525, bc - 0.01), m['Damask'], bevel=0.015)
    p(spread)
    p(box('spread_drape', (bx1 - bx0 - 0.42, 0.24, 0.025), ((bx0 + bx1) / 2 + 0.21, 0.42, bz0 - 0.03), m['Damask'], bevel=0.01))
    p(blib.subsurf(box('sheet_fold', (0.2, 0.05, bw), (bx0 + 0.52, 0.535, bc - 0.01), m['Linen'], bevel=0.02, seg=1), 1))
    pil = blib.subsurf(box('pillow', (0.36, 0.14, bw - 0.12), (bx0 + 0.24, 0.6, bc), m['Linen'], bevel=0.06, seg=1), 2)
    p(pil)
    # small table under the window: top, drawer, pedestal; a book, a glass, flowers
    tx0, tx1, tz0, tz1 = -W2 + 0.03, -W2 + 0.45, 0.55, 1.45
    tc = ((tx0 + tx1) / 2, (tz0 + tz1) / 2)
    p(box('table_top', (tx1 - tx0, 0.035, tz1 - tz0), (tc[0], 0.72, tc[1]), m['Trim'], bevel=0.012))
    p(box('table_apron', (tx1 - tx0 - 0.04, 0.1, tz1 - tz0 - 0.04), (tc[0], 0.65, tc[1]), m['Panel'], bevel=0.01))
    p(cyl('table_pull', 0.01, 0.01, 0.02, (tx1 - 0.01, 0.65, tc[1]), m['Brass'], rot=(0, 0, 90), segs=8))
    p(box('table_leg', (0.06, 0.6, 0.06), (tx1 - 0.06, 0.3, tz1 - 0.06), m['Trim'], bevel=0.01))
    p(box('book', (0.16, 0.035, 0.23), (tc[0] + 0.03, 0.755, tc[1] - 0.18), m['Leather'], bevel=0.006, rot=(0, 14, 0)))
    p(box('book_pages', (0.15, 0.025, 0.215), (tc[0] + 0.035, 0.755, tc[1] - 0.18), m['Paper'], rot=(0, 14, 0)))
    G.append(cyl('tumbler', 0.03, 0.026, 0.09, (tc[0] - 0.05, 0.783, tc[1] + 0.12), m['Glass'], segs=16))
    flowers(p, m, tc[0] - 0.06, 0.737, tc[1] + 0.32)
    # wall lamp between window and bed, ceiling dome
    lights.append({'pos': sconce(p, m, -W2 + 0.05, 1, 1.38, 1.98), 'kind': 'sconce'})
    lights.append({'pos': dome(p, m, -0.5, 1.2), 'kind': 'dome'})
    # luggage net over the door side with a suitcase, framed picture over the bed
    luggage_net(p, m, PART - 0.08, PART - 0.42, 1.86, 0.08, 1.5)
    suitcase(p, m, PART - 0.25, 1.87, 0.75, 0.55, 0.16, 0.32, m['Leather'])
    p(box('frame', (0.62, 0.46, 0.03), (-0.55, 1.5, 2.33), m['Brass'], bevel=0.012))
    p(framed_uv(box('picture', (0.54, 0.38, 0.01), (-0.55, 1.5, 2.312), m['Picture']), 0.54, 0.38))
    # a coat hook and a folding seat on the front wall
    p(tube('hook', [(-0.2, 1.62, 0.05), (-0.2, 1.62, 0.12), (-0.2, 1.68, 0.14)], 0.008, m['Brass'], segs=6))
    p(box('seat', (0.62, 0.08, 0.38), (-0.85, 0.45, 0.24), m['Damask'], bevel=0.03))
    p(box('seat_base', (0.6, 0.41, 0.34), (-0.85, 0.205, 0.22), m['Panel'], bevel=0.015))
    p(box('seat_back', (0.62, 0.42, 0.06), (-0.85, 0.78, 0.07), m['Damask'], bevel=0.025))
    bake_and_export('compartment', P, G, lights, m, res=1024,
                    moon=[((-W2 - 0.4, 1.3, 1.12), (1, 0, 0), (1.3, 0.9))])


def corridor():
    """The corridor beside one compartment (x 0.40..1.45, z 0..2.4): sliding-door opening at z 0.2..0.95."""
    m = M()
    P, G, lights = [], [], []
    p = P.append
    xm = (PART + W2) / 2
    p(box('floor', (W2 - PART, 0.04, 2.4), (xm, -0.02, 1.2), m['Floorwood']))
    p(runner('runner', 0.62, 2.4, (xm - 0.04, 0.004, 1.2), m))
    p(box('ceiling', (W2 - PART, 0.05, 2.4), (xm, H + 0.025, 1.2), m['Ceiling']))
    for xa, xb in ((PART, PART + 0.12), (W2 - 0.12, W2)):
        p(box('cove', (xb - xa, 0.08, 2.4), ((xa + xb) / 2, H - 0.04, 1.2), m['Trim'], bevel=0.02))
    # partition, corridor face, door opening z 0.2..0.95
    px = PART + 0.025
    panelled(p, m, 'x', px, 0.95, 2.4, 0, H, 1)
    p(box('part_a', (0.05, H, 0.2), (px, H / 2, 0.1), m['Panel']))
    p(box('part_top', (0.05, H - 2.0, 0.75), (px, (2.0 + H) / 2, 0.575), m['Panel']))
    for zz in (0.2, 0.95):
        p(box('door_jamb', (0.09, 2.0, 0.05), (px + 0.01, 1.0, zz), m['Trim'], bevel=0.012))
    p(box('door_head', (0.09, 0.06, 0.8), (px + 0.01, 2.02, 0.575), m['Trim'], bevel=0.012))
    p(box('number_plate', (0.012, 0.16, 0.13), (px + 0.03, 1.75, 1.08), m['Brass'], bevel=0.006))
    # outer wall with a window and a brass handrail along it
    window_wall(p, G, m, W2 - 0.025, -1, 0.0, 2.4, 0.45, 1.95, wy0=0.92, wy1=1.76, curtains=True)
    p(cyl('handrail', 0.016, 0.016, 2.4, (W2 - 0.12, 1.02, 1.2), m['Brass'], rot=(90, 0, 0), segs=12))
    for z in (0.3, 2.1):
        p(tube('rail_post', [(W2 - 0.04, 1.02, z), (W2 - 0.12, 1.02, z)], 0.01, m['Brass'], segs=6))
    lights.append({'pos': sconce(p, m, W2 - 0.05, -1, 1.5, 2.2), 'kind': 'sconce'})
    lights.append({'pos': dome(p, m, xm, 1.2), 'kind': 'dome'})
    bake_and_export('corridor', P, G, lights, m, res=1024,
                    moon=[((W2 + 0.4, 1.34, 1.2), (-1, 0, 0), (1.5, 0.84))])


def sleeper_front():
    """The front end (z -1.6..0): corridor continues to an end door; the compartment side is the washroom."""
    m = M()
    P, G, lights = [], [], []
    p = P.append
    z0, z1 = -1.6, 0.0
    zc = (z0 + z1) / 2
    p(box('floor', (2 * W2, 0.04, 1.6), (0, -0.02, zc), m['Floorwood']))
    p(runner('runner', 0.62, 1.6, ((PART + W2) / 2 - 0.04, 0.004, zc), m))
    p(box('ceiling', (2 * W2, 0.05, 1.6), (0, H + 0.025, zc), m['Ceiling']))
    panelled(p, m, 'x', PART + 0.025, z0, z1, 0, H, 1)        # washroom wall
    p(box('wc_door', (0.04, 1.95, 0.7), (PART + 0.06, 0.975, -0.8), m['Panel'], bevel=0.015))
    p(box('wc_sign', (0.01, 0.08, 0.26), (PART + 0.085, 1.72, -0.8), m['Brass'], bevel=0.004))
    p(sphere('wc_knob', 0.03, (PART + 0.1, 1.0, -0.55), m['Brass']))
    window_wall(p, G, m, W2 - 0.025, -1, z0, z1, -1.25, -0.35, wy0=0.92, wy1=1.76)
    panelled(p, m, 'z', z0 + 0.025, PART, W2, 0, H, 1)
    p(box('end_door', (0.66, 1.98, 0.05), ((PART + W2) / 2, 0.99, z0 + 0.06), m['Trim'], bevel=0.015))
    G.append(box('end_door_glass', (0.36, 0.5, 0.012), ((PART + W2) / 2, 1.45, z0 + 0.09), m['Glass']))
    p(box('end_sign', (0.4, 0.07, 0.01), ((PART + W2) / 2, 2.05, z0 + 0.09), m['Brass']))
    lights.append({'pos': dome(p, m, (PART + W2) / 2, -0.8), 'kind': 'dome'})
    bake_and_export('sleeper_front', P, G, lights, m, res=512, moon=[((W2 + 0.4, 1.34, -0.8), (-1, 0, 0), (0.9, 0.84))])


def sleeper_rear():
    """Conductor's office (compartment side, z 14.4..16.4), vestibule and the gangway to the dining car (to z 17.6)."""
    m = M()
    P, G, lights = [], [], []
    p = P.append
    z0, z1 = 14.4, 16.4
    p(box('floor', (2 * W2, 0.04, 3.2), (0, -0.02, 16.0), m['Floorwood']))
    p(runner('runner', 0.62, 2.6, ((PART + W2) / 2 - 0.04, 0.004, 15.7), m))
    p(box('ceiling', (2 * W2, 0.05, 2.6), (0, H + 0.025, 15.7), m['Ceiling']))
    # office: open half-door, desk with logbook, key board, stool
    px = PART + 0.025
    p(box('office_wall', (0.05, H, 0.7), (px, H / 2, z0 + 0.35), m['Panel']))
    p(box('office_wall2', (0.05, H, 0.6), (px, H / 2, z1 - 0.3), m['Panel']))
    p(box('half_door', (0.05, 1.0, 0.68), (px, 0.5, 15.45), m['Panel'], bevel=0.012))
    p(box('half_door_top', (0.12, 0.04, 0.72), (px, 1.02, 15.45), m['Trim'], bevel=0.01))
    p(box('office_head', (0.05, H - 2.0, 0.7), (px, (2.0 + H) / 2, 15.45), m['Panel']))
    window_wall(p, G, m, -W2 + 0.025, 1, z0, z1, 14.75, 16.05, curtains=False)
    panelled(p, m, 'z', z0 + 0.025, -W2, PART, 0, H, -1)
    panelled(p, m, 'z', z1 - 0.025, -W2, PART, 0, H, 1)
    p(box('desk', (0.5, 0.04, 1.2), (-W2 + 0.3, 0.76, 15.4), m['Trim'], bevel=0.012))
    p(box('desk_body', (0.46, 0.72, 0.5), (-W2 + 0.3, 0.37, 15.0), m['Panel'], bevel=0.012))
    p(box('logbook', (0.24, 0.03, 0.34), (-W2 + 0.32, 0.795, 15.6), m['Leather'], bevel=0.005))
    p(box('logbook_page', (0.22, 0.004, 0.32), (-W2 + 0.33, 0.812, 15.6), m['Paper']))
    p(box('keyboard', (0.02, 0.5, 0.6), (-W2 + 0.06, 1.45, 15.6), m['Trim'], bevel=0.01))
    for i in range(6):
        k = (-W2 + 0.09, 1.6 - (i // 3) * 0.2, 15.42 + (i % 3) * 0.17)
        p(tube('key_hook', [k, (k[0] + 0.03, k[1], k[2])], 0.004, m['Brass'], segs=4))
        p(box('key_tag', (0.006, 0.07, 0.04), (k[0] + 0.035, k[1] - 0.06, k[2]), m['Brass']))
    p(cyl('stool', 0.17, 0.17, 0.05, (-0.6, 0.48, 15.3), m['Leather'], segs=20))
    p(cyl('stool_leg', 0.03, 0.05, 0.46, (-0.6, 0.23, 15.3), m['Brass'], segs=10))
    lights.append({'pos': sconce(p, m, -W2 + 0.05, 1, 1.45, 14.65), 'kind': 'sconce'})
    # corridor side of this stretch
    window_wall(p, G, m, W2 - 0.025, -1, z0, z1, 14.7, 16.1, wy0=0.92, wy1=1.76)
    p(cyl('handrail', 0.016, 0.016, 2.0, (W2 - 0.12, 1.02, 15.4), m['Brass'], rot=(90, 0, 0), segs=12))
    lights.append({'pos': dome(p, m, (PART + W2) / 2, 15.4), 'kind': 'dome'})
    # vestibule 16.4..17.0 and gangway bellows 17.0..17.6
    for s in (-1, 1):
        p(box('vest_wall', (0.05, H, 0.6), (s * (W2 - 0.025), H / 2, 16.7), m['Panel']))
    p(box('end_left', (W2 + PART - 0.25, H, 0.06), ((-W2 + PART - 0.25) / 2 + 0.0, H / 2, 17.0), m['Panel']))
    p(box('end_right', (W2 - PART - 0.75 + 0.25, H, 0.06), (W2 - (W2 - PART - 0.5) / 2, H / 2, 17.0), m['Panel']))
    for s in (-1, 1):
        p(box('bellows', (0.04, 2.1, 0.6), (s * 0.55, 1.05, 17.3), m['Bellows']))
    p(box('bellows_top', (1.14, 0.04, 0.6), (0, 2.1, 17.3), m['Bellows']))
    p(box('plate', (1.1, 0.02, 0.6), (0, 0.0, 17.3), m['Iron']))
    for k in range(6):
        for s in (-1, 1):
            p(box('fold', (0.03, 2.06, 0.03), (s * 0.53, 1.03, 17.05 + k * 0.1), m['Black']))
    bake_and_export('sleeper_rear', P, G, lights, m, res=1024,
                    moon=[((-W2 - 0.4, 1.3, 15.4), (1, 0, 0), (1.3, 0.9)), ((W2 + 0.4, 1.34, 15.4), (-1, 0, 0), (1.4, 0.84))])


def dining_walls(p, G, m, z0, z1, wins):
    for x, s in ((-W2 + 0.025, 1), (W2 - 0.025, -1)):
        for (a, b, wa, wb) in wins:
            window_wall(p, G, m, x, s, a, b, wa, wb, wy0=0.86, wy1=1.8)


def dining_bay():
    """One dining bay (z 0..2.4): a four-seat booth on the left, a two-seat table on the right, lamps, place settings."""
    m = M()
    P, G, lights = [], [], []
    p = P.append
    p(box('floor', (2 * W2, 0.04, 2.4), (0, -0.02, 1.2), m['Carpet']))
    p(runner('runner', 0.7, 2.4, (0, 0.004, 1.2), m))
    # arched ceiling with a raised clerestory strip
    p(box('ceiling', (2 * W2, 0.05, 2.4), (0, H + 0.025, 1.2), m['Ceiling']))
    p(box('clerestory', (0.9, 0.04, 2.4), (0, H + 0.18, 1.2), m['Ceiling']))
    for s in (-1, 1):
        p(box('cler_side', (0.04, 0.18, 2.4), (s * 0.45, H + 0.09, 1.2), m['Trim']))
        p(box('cove', (0.18, 0.08, 2.4), (s * (W2 - 0.09), H - 0.04, 1.2), m['Trim'], bevel=0.02))
    dining_walls(p, G, m, 0, 2.4, [(0, 2.4, 0.4, 2.0)])
    for s, seats in ((-1, 4), (1, 2)):
        tx = s * (W2 - 0.42 if seats == 4 else W2 - 0.32)
        tw = 0.72 if seats == 4 else 0.52
        # table with cloth, lamp, place settings
        p(box('table', (tw, 0.04, 0.8), (tx, 0.74, 1.2), m['Trim'], bevel=0.01))
        p(box('cloth', (tw + 0.06, 0.02, 0.86), (tx, 0.765, 1.2), m['Tablecloth'], bevel=0.008))
        p(box('cloth_drop', (0.012, 0.16, 0.86), (tx - s * (tw / 2 + 0.03), 0.69, 1.2), m['Tablecloth']))
        p(cyl('pedestal', 0.04, 0.04, 0.72, (tx, 0.36, 1.2), m['Brass'], segs=12))
        p(box('wall_bracket', (0.08, 0.1, 0.4), (s * (W2 - 0.06), 0.7, 1.2), m['Brass'], bevel=0.01))
        lx = s * (W2 - 0.15)
        p(cyl('lamp_base', 0.05, 0.04, 0.02, (lx, 0.785, 1.2), m['Brass'], segs=16))
        p(cyl('lamp_stem', 0.008, 0.008, 0.22, (lx, 0.9, 1.2), m['Brass'], segs=8))
        p(cyl('lamp_shade', 0.08, 0.045, 0.1, (lx, 1.04, 1.2), m['Shade'], segs=20, cap=False))
        p(sphere('lamp_bulb', 0.02, (lx, 1.02, 1.2), m['Bulb'], segs=8, rings=6))
        lights.append({'pos': (lx, 1.02, 1.2), 'kind': 'table_lamp'})
        for dz in (-0.25, 0.25):
            for k in range(seats // 2):
                px = tx + (k - (seats // 2 - 1) / 2) * 0.32
                p(cyl('plate', 0.1, 0.09, 0.012, (px, 0.782, 1.2 + dz), m['Ceramic'], segs=24))
                p(box('fork', (0.012, 0.004, 0.17), (px - 0.13, 0.778, 1.2 + dz), m['Silver']))
                p(box('knife', (0.014, 0.004, 0.19), (px + 0.13, 0.778, 1.2 + dz), m['Silver']))
                G.append(cyl('wine_glass', 0.028, 0.022, 0.07, (px + 0.1, 0.84, 1.2 + dz * 0.7), m['Glass'], segs=12))
        # benches facing each other
        bx0, bx1 = (s * W2 - s * 0.03, tx - s * (tw / 2) + s * 0.0) if seats == 4 else (s * W2 - s * 0.03, tx - s * (tw / 2))
        bxc, bxw = (bx0 + bx1) / 2, abs(bx1 - bx0) + 0.1
        for face in (-1, 1):
            z = 1.2 - face * 0.72
            p(blib.subsurf(box('cushion', (bxw - 0.04, 0.12, 0.46), (bxc, 0.46, z), m['Damask'], bevel=0.035, seg=1), 1))
            p(box('bench', (bxw, 0.4, 0.44), (bxc, 0.2, z), m['Panel'], bevel=0.015))
            p(blib.subsurf(box('back', (bxw - 0.04, 0.62, 0.12), (bxc, 0.86, 1.2 - face * 0.98), m['Damask'], bevel=0.04, seg=1, rot=(face * 6, 0, 0)), 1))
            p(box('back_shell', (bxw, 1.15, 0.05), (bxc, 0.6, 1.2 - face * 1.08), m['Panel'], bevel=0.015))
            p(box('back_cap', (bxw, 0.04, 0.1), (bxc, 1.19, 1.2 - face * 1.07), m['Trim'], bevel=0.012))
    lights.append({'pos': dome(p, m, 0, 1.2, H + 0.16), 'kind': 'dome'})
    bake_and_export('dining_bay', P, G, lights, m, res=1024,
                    moon=[((-W2 - 0.4, 1.33, 1.2), (1, 0, 0), (1.6, 0.94)), ((W2 + 0.4, 1.33, 1.2), (-1, 0, 0), (1.6, 0.94))])


def dining_end():
    """Bar, coal stove and armchairs, and the locked door to the baggage car (z 0..4.8 locally; placed at 27.2)."""
    m = M()
    P, G, lights = [], [], []
    p = P.append
    L = 4.8
    p(box('floor', (2 * W2, 0.04, L), (0, -0.02, L / 2), m['Carpet']))
    p(runner('runner', 0.7, L - 0.4, (0, 0.004, L / 2 - 0.2), m))
    p(box('ceiling', (2 * W2, 0.05, L), (0, H + 0.025, L / 2), m['Ceiling']))
    p(box('clerestory', (0.9, 0.04, L), (0, H + 0.18, L / 2), m['Ceiling']))
    for s in (-1, 1):
        p(box('cler_side', (0.04, 0.18, L), (s * 0.45, H + 0.09, L / 2), m['Trim']))
    dining_walls(p, G, m, 0, L, [(0, 2.4, 0.4, 2.0), (2.4, L, 2.8, 4.0)])
    # bar counter on the right: marble top, panelled front, brass foot rail, back shelves with bottles
    bx = W2 - 0.55
    p(box('bar_front', (0.06, 1.05, 2.2), (bx - 0.25, 0.525, 1.5), m['Panel'], bevel=0.015))
    p(box('bar_top', (0.6, 0.05, 2.3), (bx, 1.08, 1.5), m['Marble'], bevel=0.012))
    p(box('bar_body', (0.5, 1.03, 2.2), (bx + 0.03, 0.515, 1.5), m['Trim']))
    p(cyl('foot_rail', 0.018, 0.018, 2.2, (bx - 0.36, 0.18, 1.5), m['Brass'], rot=(90, 0, 0), segs=10))
    for i, z in enumerate((0.7, 1.5, 2.3)):
        p(cyl('stool', 0.17, 0.17, 0.06, (bx - 0.6, 0.72, z), m['Leather'], segs=20))
        p(cyl('stool_leg', 0.025, 0.05, 0.7, (bx - 0.6, 0.35, z), m['Brass'], segs=10))
    sx = W2 - 0.12
    for y in (1.3, 1.62):
        p(box('shelf', (0.2, 0.025, 2.0), (sx, y, 1.5), m['Trim'], bevel=0.006))
        rng = random.Random(int(y * 10))
        for k in range(10):
            mm = m['Bottle'] if k % 3 else m['Amber']
            G.append(cyl('bottle', 0.03, 0.03, 0.2, (sx, y + 0.11, 0.6 + k * 0.19 + rng.random() * 0.04), mm, segs=12))
    p(box('mirror_frame', (0.03, 0.5, 1.6), (W2 - 0.03, 1.95, 1.5), m['Brass'], bevel=0.01))
    # coal stove on the left: cast-iron body, glowing grate, flue, coal scuttle; two armchairs
    stx, stz = -W2 + 0.4, 1.6
    p(box('hearth', (0.7, 0.04, 0.8), (stx, 0.02, stz), m['Marble'], bevel=0.01))
    p(cyl('stove', 0.24, 0.26, 0.75, (stx, 0.42, stz), m['Iron'], segs=24))
    p(cyl('stove_top', 0.28, 0.28, 0.05, (stx, 0.82, stz), m['Iron'], segs=24))
    p(box('grate', (0.05, 0.16, 0.24), (stx + 0.24, 0.38, stz), m['Fire']))
    p(cyl('flue', 0.07, 0.07, 1.4, (stx, 1.55, stz), m['Iron'], segs=16))
    p(box('scuttle', (0.3, 0.25, 0.22), (stx + 0.05, 0.13, stz + 0.55), m['Iron'], bevel=0.02))
    for k in range(8):
        p(sphere('coal', 0.04, (stx + 0.0 + (k % 4) * 0.06 - 0.06, 0.26, stz + 0.5 + (k // 4) * 0.06), m['Coal'], segs=6, rings=4))
    lights.append({'pos': (stx + 0.4, 0.4, stz), 'kind': 'fire'})
    for z in (0.5, 2.8):
        ac = (-W2 + 0.55, z)
        p(blib.subsurf(box('arm_seat', (0.55, 0.14, 0.55), (ac[0], 0.42, ac[1]), m['Velvet'], bevel=0.05, seg=1), 1))
        p(blib.subsurf(box('arm_back', (0.12, 0.6, 0.6), (ac[0] - 0.24, 0.75, ac[1]), m['Velvet'], bevel=0.05, seg=1), 1))
        for dz in (-0.3, 0.3):
            p(blib.subsurf(box('arm_rest', (0.55, 0.22, 0.1), (ac[0], 0.58, ac[1] + dz), m['Velvet'], bevel=0.04, seg=1), 1))
        p(box('arm_base', (0.55, 0.32, 0.6), (ac[0], 0.18, ac[1]), m['Panel'], bevel=0.02))
    lights.append({'pos': sconce(p, m, -W2 + 0.05, 1, 1.5, 3.6), 'kind': 'sconce'})
    lights.append({'pos': sconce(p, m, W2 - 0.05, -1, 1.5, 3.4), 'kind': 'sconce'})
    lights.append({'pos': dome(p, m, 0, 1.5, H + 0.16), 'kind': 'dome'})
    # end wall with the locked baggage-car door (barred window), a notice and a padlock
    z = L - 0.025
    panelled(p, m, 'z', z, -W2, -0.42, 0, H + 0.2, -1, rail=0.95)
    panelled(p, m, 'z', z, 0.42, W2, 0, H + 0.2, -1, rail=0.95)
    p(box('door_head', (0.84, H + 0.2 - 2.0, 0.05), (0, (2.0 + H + 0.2) / 2, z), m['Panel']))
    p(box('bag_door', (0.8, 2.0, 0.07), (0, 1.0, z - 0.02), m['Iron'], bevel=0.01))
    G.append(box('bag_window', (0.3, 0.22, 0.012), (0, 1.55, z - 0.06), m['Glass']))
    for k in range(5):
        p(cyl('bar', 0.007, 0.007, 0.24, (-0.12 + k * 0.06, 1.55, z - 0.07), m['Iron'], segs=6))
    p(box('hasp', (0.12, 0.05, 0.02), (0.3, 1.1, z - 0.07), m['Brass'], bevel=0.005))
    p(torus('padlock_shackle', 0.03, 0.007, (0.3, 1.06, z - 0.08), m['Silver'], rot=(90, 0, 0), segs=12, rsegs=5))
    p(box('padlock', (0.07, 0.07, 0.03), (0.3, 1.01, z - 0.08), m['Brass'], bevel=0.008))
    p(box('notice', (0.32, 0.22, 0.01), (-0.75, 1.5, z - 0.03), m['Paper']))
    bake_and_export('dining_end', P, G, lights, m, res=1024,
                    moon=[((-W2 - 0.4, 1.33, 1.2), (1, 0, 0), (1.6, 0.94)), ((W2 + 0.4, 1.33, 1.2), (-1, 0, 0), (1.6, 0.94)),
                          ((-W2 - 0.4, 1.33, 3.4), (1, 0, 0), (1.2, 0.94)), ((W2 + 0.4, 1.33, 3.4), (-1, 0, 0), (1.2, 0.94))])


# ------------------------------------------------------------------ bake + export
LIGHT_W = {'sconce': 14.0, 'dome': 22.0, 'table_lamp': 9.0, 'fire': 30.0}
LIGHT_C = {'sconce': WARM, 'dome': (1.0, 0.78, 0.55), 'table_lamp': WARM, 'fire': (1.0, 0.45, 0.15)}


def bake_and_export(name, parts, glass, lights, m, res, moon):
    merged = blib.merge(parts, name)
    blib.box_uv(merged, UV_SCALE)
    blib.lightmap_uv(merged)
    for gobj in glass:
        gobj.hide_render = True  # windows are open to the night for the bake
    world_sky((0.05, 0.07, 0.12), 0.35)
    bl = [point_light('L', l['pos'], LIGHT_C[l['kind']], LIGHT_W[l['kind']], 0.09) for l in lights]
    for (pos, facing, size) in moon:
        bl.append(area_light('moon', pos, MOON, 26.0 * size[0] * size[1], size, facing))
    blib.bake_lightmap(merged, 256 if FAST else res, os.path.join(OUT, name + '_lm.png'),
                       samples=16 if FAST else 160, scale=2.0, blur=0.8 if FAST else 1.1)
    for o in bl:
        blib.bpy.data.objects.remove(o, do_unlink=True)
    for gobj in glass:
        gobj.hide_render = False
    out = [merged]
    if glass:
        out.append(blib.merge(glass, name + '_glass'))
    blib.export_objects(out, os.path.join(OUT, name + '.glb'))
    with open(os.path.join(OUT, name + '_lights.json'), 'w') as f:
        json.dump([{'pos': list(l['pos']), 'kind': l['kind']} for l in lights], f, indent=1)


MODULES = {'compartment': compartment, 'corridor': corridor, 'sleeper_front': sleeper_front,
           'sleeper_rear': sleeper_rear, 'dining_bay': dining_bay, 'dining_end': dining_end}

if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(MODULES)
    for n in names:
        reset()
        MODULES[n]()
