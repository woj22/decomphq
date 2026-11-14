"""The Imperial Balcony vista, rebuilt around the reference's composition (reference/balcony_target.png).

Run:  python3 imperium/blender/vista.py [--samples N] [--res WxH] [--no-walkers]
Writes renders/vista.png (and renders/compare_vista.png beside the reference).

Composition (measured from the reference, 24 mm lens, 16:9):
  camera 2.9 m above the balcony floor, pitched 5 degrees down, the palace standing ~80 m above the city;
  the balustrade runs obliquely - close on the right (fire bowl), receding left past the statue;
  the forum fountain ~360 m out, slightly right of centre; the capitol on its hill ~600 m out, right of centre;
  the sun low on the right, ~23 degrees off-axis and just above the horizon.
Depth: foreground balcony; a dense, varied middle ground; a city that dissolves into haze toward the
mountains. Aerial perspective is done in the shaders (view distance -> haze), not baked into colours.
World axes: the camera looks along -Y; screen-right is -X.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import kharad as K  # noqa: E402
import cast as C  # noqa: E402
import palace as P  # noqa: E402
import city as T  # noqa: E402
from city import Acc, at, ring, insula, domus, temple, tree, banner_flat, hip_roof, arcade_wall, aqueduct, amphitheatre  # noqa: E402

ROOT = K.ROOT
H_CAM = 2.86
PITCH = math.radians(-5.0)
LENS = 24.0
CITY = -40.0                                   # city ground relative to the balcony floor
SUN = Vector((-math.sin(math.radians(23)), -math.cos(math.radians(23)), math.tan(math.radians(3.4)))).normalized()
PLAZA = Vector((-19.5, -188.0))
CAPITOL = Vector((-60.0, -420.0))
HAZE = "e2b2a6"
MARBLE, MARBLE2, CRIMSON, GOLD = T.MARBLE, T.MARBLE2, T.CRIMSON, T.GOLD

# the balustrade line: near-right end to far-left end (solved from the reference's screen positions)
BAL_R = Vector((-4.9, -5.95))
BAL_L = Vector((9.5, -10.35))


def bal_y(x):
    t = (x - BAL_R.x) / (BAL_L.x - BAL_R.x)
    return BAL_R.y + (BAL_L.y - BAL_R.y) * t


# ----------------------------------------------------------------------------- the city
def plan_city(rng):
    """Returns the list of accumulators (chunked by distance band) with the whole city written in."""
    accs = {}

    def acc(x, y):
        dist = math.hypot(x, y)
        band = 0 if dist < 700 else 1 if dist < 1500 else 2
        k = (band, int((x + 4000) // 400), int((y + 4000) // 400))
        if k not in accs:
            accs[k] = Acc("Vista_%d_%d_%d" % k)
        return accs[k], dist

    g, _ = acc(0, -500)
    g.T = Matrix.Identity(4)
    g.poly([(-6000, -7000, CITY - 0.5), (6000, -7000, CITY - 0.5), (6000, 400, CITY - 0.5), (-6000, 400, CITY - 0.5)], g.key("b49c7a"))
    g.poly([(-1700, -3400, CITY), (1700, -3400, CITY), (1700, -60, CITY), (-1700, -60, CITY)], g.key("cbb593"))

    # the palace hill falling away below the balcony: terraces, retaining walls and trees
    for k, (y0, y1, z) in enumerate(((-12, -30, -16), (-30, -52, -31))):
        g.box((0, (y0 + y1) / 2, (z + CITY) / 2), (260, abs(y1 - y0), z - CITY), g.key("cdb99a"))
        g.box((0, y1 + 0.5, z - 0.6), (262, 1.2, 1.2), g.key(MARBLE))
        for q in range(18):
            tree(g, (rng.uniform(-120, 120), rng.uniform(y1 + 3, y0 - 3), z), rng.uniform(6, 9), "cypress")

    # street grid: districts with their own block size, rotation and density
    occupied = []

    def free(x, y, r):
        if (Vector((x, y)) - PLAZA).length < 44 + r:
            return False
        if abs(x - CAPITOL.x) < 210 + r and abs(y - CAPITOL.y) < 190 + r:
            return False
        # the processional way from the forum to the capitol stair
        ax, ay = PLAZA
        bx, by = CAPITOL.x + 10, CAPITOL.y + 190
        t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        if math.hypot(x - (ax + (bx - ax) * t), y - (ay + (by - ay) * t)) < 16 + r:
            return False
        return y < -62
    walls = T.WALLS
    for gx in range(-70, 71):
        for gy in range(2, 112):
            base = 30.0
            x = gx * base + rng.uniform(-4, 4)
            y = -gy * base + rng.uniform(-4, 4)
            dist = math.hypot(x, y)
            if dist > 3300 or not free(x, y, 10):
                continue
            # thin out to the sides at distance so the skyline reads, keep it dense ahead
            if abs(math.atan2(-x, -y)) > math.radians(50) and dist < 220:
                continue
            a, dist = acc(x, y)
            yaw = rng.choice((0.0, 0.0, math.radians(rng.uniform(-12, 12))))
            if dist < 760:
                roll = rng.random()
                at(a, x, y, CITY, yaw)
                if roll < 0.05:
                    a.T = a.T @ Matrix.Rotation(math.pi, 4, "Z")
                    temple(a, rng.uniform(11, 15), rng.uniform(16, 22), rng.uniform(7, 9), rng, True)
                elif roll < 0.1:
                    domus(a, rng.uniform(20, 26), rng, True)
                elif roll < 0.14:
                    a.box((0, 0, 0.15), (26, 26, 0.3), a.key("6f8f45"))
                    for _ in range(rng.randint(4, 9)):
                        tree(a, (rng.uniform(-12, 12), rng.uniform(-12, 12), 0.3), rng.uniform(8, 13), "cypress" if rng.random() < 0.6 else "pine")
                elif roll < 0.17:
                    # a tower: tall, narrow, with a tiled pyramid cap
                    h = rng.uniform(22, 34)
                    a.box((0, 0, h / 2), (7, 7, h), a.key(rng.choice(walls)))
                    for f in range(int(h / 4)):
                        a.box((0, 3.52, 2.5 + f * 4), (1.0, 0.05, 1.6), a.key("5e4038"))
                    a.box((0, 0, h - 0.2), (8, 8, 0.4), a.key(MARBLE))
                    hip_roof(a, 7, 7, h, a.key(T.ROOF), a.key("8a3a28"), 0.6, 0.9)
                elif roll < 0.2:
                    # a rotunda with a dome
                    a.stack([(0, ring(14, 9, 9), 0, 0), (9, ring(14, 9, 9), 0, 0)], a.key(rng.choice(walls)), False, False)
                    for q in range(14):
                        ang = 2 * math.pi * q / 14
                        a.tube([(math.cos(ang) * 9.6, math.sin(ang) * 9.6, 0), (math.cos(ang) * 9.6, math.sin(ang) * 9.6, 8.5)], [0.4, 0.35], a.key(MARBLE), 8)
                    secs = [(9 + math.sin(t * math.pi / 2) * 7, ring(14, max(0.4, math.cos(t * math.pi / 2) * 9.4), max(0.4, math.cos(t * math.pi / 2) * 9.4)), 0, 0) for t in (0, 0.3, 0.55, 0.78, 1.0)]
                    a.stack(secs, a.key(T.ROOF), False, True)
                else:
                    # one to four insulae of different heights, packed tight
                    split = rng.choice(((1, 1), (2, 1), (1, 2), (2, 2), (2, 2)))
                    for u in range(split[0]):
                        for v in range(split[1]):
                            bw = (base - 4) / split[0] - 0.6
                            bd = (base - 4) / split[1] - 0.6
                            at(a, x - (base - 4) / 2 + (u + 0.5) * (base - 4) / split[0], y - (base - 4) / 2 + (v + 0.5) * (base - 4) / split[1], CITY, yaw)
                            fl = rng.choice((2, 3, 3, 3, 4, 4, 5)) if dist < 500 else rng.choice((2, 3, 3, 4))
                            insula(a, bw * rng.uniform(0.86, 1.0), bd * rng.uniform(0.86, 1.0), fl, rng, True, dist < 420)
                    if rng.random() < 0.3:
                        a.T = Matrix.Identity(4)
                        tree(a, (x + rng.uniform(-14, 14), y + base / 2 - 1, CITY), rng.uniform(8, 12), "cypress")
            elif dist < 1600:
                # medium detail: massing, roofs, a cornice and a few window bands
                at(a, x, y, CITY, yaw)
                for u in range(rng.choice((1, 2))):
                    w = rng.uniform(10, 24)
                    d = rng.uniform(10, 24)
                    h = rng.uniform(7, 16)
                    off = rng.uniform(-6, 6)
                    keep = a.T
                    a.T = a.T @ Matrix.Translation((off, rng.uniform(-6, 6), 0))
                    a.box((0, 0, h / 2), (w, d, h), a.key(rng.choice(walls)))
                    a.box((0, 0, h - 0.2), (w + 0.4, d + 0.4, 0.4), a.key(MARBLE))
                    for f in range(int(h / 3.4)):
                        a.box((0, d / 2 + 0.02, 2.2 + f * 3.4), (w * 0.8, 0.05, 1.0), a.key("8a6a5e"))
                    hip_roof(a, w, d, h, a.key(T.ROOF), a.key("8a3a28"), 0.5, rng.uniform(0.25, 0.35))
                    a.T = keep
                if rng.random() < 0.12:
                    a.T = Matrix.Identity(4)
                    tree(a, (x, y + 12, CITY), 12, "cypress")
            else:
                at(a, x, y, CITY, 0.0)
                w, d, h = rng.uniform(14, 28), rng.uniform(14, 28), rng.uniform(8, 18)
                a.box((0, 0, h / 2), (w, d, h), a.key(rng.choice(walls)))
                hip_roof(a, w, d, h, a.key(T.ROOF), a.key("8a3a28"), 0.5, 0.3)
    for a in accs.values():
        a.T = Matrix.Identity(4)

    # the forum: paving, colonnades, banners, the statue fountain, an arch toward the capitol
    a, _ = acc(PLAZA.x, PLAZA.y)
    a.T = Matrix.Identity(4)
    fx, fy = PLAZA
    a.box((fx, fy, CITY + 0.1), (72, 60, 0.2), a.key("e8ddc8"))
    for i in range(9):
        for j in range(8):
            if (i + j) % 2 == 0:
                a.poly([(fx - 36 + i * 8, fy - 30 + j * 7.5, CITY + 0.21), (fx - 28 + i * 8, fy - 30 + j * 7.5, CITY + 0.21),
                        (fx - 28 + i * 8, fy - 22.5 + j * 7.5, CITY + 0.21), (fx - 36 + i * 8, fy - 22.5 + j * 7.5, CITY + 0.21)], a.key("d6c6aa"))
    for side in (-1, 1):
        x0 = fx + side * 34
        for k in range(14):
            y = fy - 28 + k * 4.3
            a.stack([(CITY, ring(10, 0.55, 0.55, 0.04), x0, y), (CITY + 8, ring(10, 0.46, 0.46, 0.04), x0, y)], a.key(MARBLE))
        a.box((x0, fy, CITY + 8.5), (1.8, 58, 1.0), a.key(MARBLE))
        a.box((x0, fy, CITY + 9.2), (1.9, 58, 0.4), a.key(CRIMSON))
        a.box((x0 + side * 5, fy, CITY + 6.0), (8, 58, 12), a.key("efe2cc"))
        T.hip_roof_at(a, x0 + side * 4, fy, 11, 60, CITY + 12)
        for k in range(4):
            banner_flat(a, (x0 - side * 1.0, fy - 22 + k * 14, CITY + 8.2), 2.4, 5.8, -side * math.pi / 2)
    # fountain with a tall statue
    a.stack([(CITY + 0.2, ring(12, 11, 11), fx, fy), (CITY + 1.4, ring(12, 11, 11), fx, fy)], a.key(MARBLE))
    a.stack([(CITY + 1.2, ring(12, 10.2, 10.2), fx, fy), (CITY + 1.25, ring(12, 10.2, 10.2), fx, fy)], a.key("5aa3c4", 0.05))
    a.stack([(CITY + 1.2, ring(8, 2.6, 2.6), fx, fy), (CITY + 7.5, ring(8, 2.0, 2.0), fx, fy)], a.key(MARBLE2))
    T.arch(a, fx - 6, fy - 36, CITY, math.radians(-12))
    a.T = Matrix.Identity(4)
    # the processional way: a colonnaded avenue with cypresses and banner poles
    ax, ay = fx, fy - 32
    bx, by = CAPITOL.x + 10, CAPITOL.y + 196
    n = 22
    for k in range(n):
        t = k / (n - 1)
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        for sx in (-1, 1):
            tree(a, (x + sx * 13, y, CITY), 10, "cypress")
            if k % 3 == 1:
                a.tube([(x + sx * 9, y, CITY), (x + sx * 9, y, CITY + 11)], [0.15, 0.12], a.key(GOLD, 0.5, 0.4), 5)
                banner_flat(a, (x + sx * 9, y + 0.3, CITY + 10.6), 1.8, 5.0, math.pi)

    # the capitol: a hill with arcaded terraces, a grand stair, flanking temples, the great temple on top
    a, _ = acc(CAPITOL.x, CAPITOL.y)
    a.T = Matrix.Identity(4)
    cx, cy = CAPITOL
    z = CITY
    tiers = ((300, 250, 16), (235, 196, 15), (176, 148, 15), (124, 106, 13), (84, 74, 10))
    for li, (w, d, h) in enumerate(tiers):
        a.box((cx, cy, z + h / 2), (w, d, h), a.key("ddd0b8" if li % 2 else "e6dac4"))
        a.box((cx, cy, z + h - 0.4), (w + 1.5, d + 1.5, 0.8), a.key(MARBLE))
        arcade_wall(a, cx - w / 2, cx + w / 2, cy + d / 2 + 0.01, z, h, (cx - 26, cx + 26))
        top = z + h
        if li < len(tiers) - 1:
            nw, nd = tiers[li + 1][0], tiers[li + 1][1]
            # buildings and trees on the terrace ring
            for k in range(12):
                for side in (-1, 1):
                    bxp = cx + side * (nw / 2 + (w - nw) / 4)
                    byp = cy - d / 2 + 18 + k * (d - 36) / 11
                    at(a, bxp, byp, top, math.pi)
                    if k % 4 == 2:
                        temple(a, 12, 16, 8, rng, True)
                    elif k % 4 == 0:
                        a.T = Matrix.Identity(4)
                        tree(a, (bxp, byp, top), 11, "cypress")
                    else:
                        insula(a, (w - nw) / 2 - 10, 14, rng.choice((2, 3)), rng, True)
            for k in range(14):
                x = cx - nw / 2 + 6 + k * (nw - 12) / 13
                if abs(x - cx) < 30:
                    continue
                at(a, x, cy + nd / 2 + (d - nd) / 4, top, math.pi)
                if k % 3 == 0:
                    a.T = Matrix.Identity(4)
                    tree(a, (x, cy + nd / 2 + (d - nd) / 4, top), 11, "cypress")
                else:
                    insula(a, 11, (d - nd) / 2 - 8, 2, rng, True)
            for k in range(0, int(w / 16)):
                x = cx - w / 2 + 8 + k * 16
                if abs(x - cx) > 30 and k % 2 == 0:
                    a.T = Matrix.Identity(4)
                    banner_flat(a, (x, cy + d / 2 + 0.6, top - 1.0), 3.4, h * 0.6, math.pi)
        z = top
    # the grand stair: flights between landings, alternating tread colours, walls with banners
    y0 = cy + tiers[0][1] / 2 + 30
    y1 = cy + tiers[-1][1] / 2
    zt = CITY
    nfl = len(tiers)
    for f in range(nfl):
        fy0 = y0 - (y0 - y1) * f / nfl
        fy1 = y0 - (y0 - y1) * (f + 0.78) / nfl
        rise = tiers[f][2]
        steps = 16
        w = 30 - f * 3.5
        for i in range(steps):
            t = i / steps
            y = fy0 - (fy0 - fy1) * t
            a.box((cx, y, zt + rise * (i + 0.5) / steps / 2), (w, (fy0 - fy1) / steps + 0.2, rise * (i + 1) / steps),
                  a.key(MARBLE if i % 2 == 0 else "dcd0bc"))
        land_y = (fy1 + y0 - (y0 - y1) * (f + 1) / nfl) / 2
        a.box((cx, land_y, zt + rise - 0.2), (w + 2, (fy1 - (y0 - (y0 - y1) * (f + 1) / nfl)) + 0.4, 0.4), a.key("e2d6c2"))
        for sx in (-1, 1):
            wx = cx + sx * (w / 2 + 1.2)
            a.box((wx, (fy0 + fy1) / 2, zt + rise / 2 + 0.6), (2.4, fy0 - fy1, rise + 1.2), a.key("e8dcc6"))
            a.cone((wx, fy0, zt + 1.2), 0.7, 1.4, a.key(GOLD, 0.5, 0.4), 4)
            banner_flat(a, (wx, fy0 + 0.2, zt + rise * 0.9 + 0.6), 2.2, rise * 0.7, math.pi)
        zt += rise
    at(a, cx, cy - 6, z, math.pi)
    temple(a, 50, 64, 22, rng, True)
    a.T = Matrix.Identity(4)
    a.tube([(cx, cy - 6, z + 28), (cx, cy - 6, z + 52)], [2.6, 0.2], a.key(GOLD, 0.4, 0.5), 8)
    for sx in (-1, 1):
        at(a, cx + sx * 50, cy + 6, z - tiers[-1][2], math.pi)
        temple(a, 22, 28, 12, rng, True)

    # landmark palaces framing the middle ground (as in the reference): colonnades, banners, tiled roofs
    for (lx, ly, w, d, fl) in ((-118, -205, 44, 26, 4), (-160, -270, 38, 24, 4), (52, -240, 40, 24, 4), (-82, -150, 30, 20, 3)):
        a, _ = acc(lx, ly)
        at(a, lx, ly, CITY, math.radians(rng.uniform(-6, 6)))
        H = fl * 3.4 + 0.5
        a.box((0, 0, H / 2), (w, d, H), a.key("efe3cf"))
        a.box((0, 0, H - 0.15), (w + 0.6, d + 0.6, 0.4), a.key(MARBLE))
        a.box((0, 0, H + 0.45), (w + 0.3, d + 0.3, 0.6), a.key(CRIMSON))
        for f in range(fl):
            zc = f * 3.4
            a.box((0, d / 2 + 1.6, zc + 0.15), (w, 3.2, 0.3), a.key(MARBLE))
            for k in range(int(w / 3.2) + 1):
                xk = -w / 2 + k * w / int(w / 3.2)
                a.stack([(zc + 0.3, ring(8, 0.42, 0.42), xk, d / 2 + 2.6), (zc + 3.2, ring(8, 0.36, 0.36), xk, d / 2 + 2.6)], a.key(MARBLE))
            a.poly([(-w / 2, d / 2 + 0.02, zc + 0.3), (w / 2, d / 2 + 0.02, zc + 0.3), (w / 2, d / 2 + 0.02, zc + 3.1), (-w / 2, d / 2 + 0.02, zc + 3.1)][::-1], a.key("8a6a5e"))
        hip_roof(a, w + 3, d + 5, H + 0.75, a.key(T.ROOF), a.key("8a3a28"), 0.8, 0.28)
        for k in range(3):
            banner_flat(a, (-w / 3 + k * w / 3, d / 2 + 3.4, H - 0.6), 3.0, H * 0.62, math.pi)
        a.T = Matrix.Identity(4)
        for q in range(3):
            tree(a, (lx + rng.uniform(-w / 2, w / 2), ly + d / 2 + 7, CITY), rng.uniform(9, 13), "cypress")

    # the aqueduct across the right, the amphitheatre on the left
    a, _ = acc(-700, -1300)
    a.T = Matrix.Identity(4)
    aqueduct(a, (-1800, -1700, 0), (-260, -880, 0), CITY, 34)
    a2, _ = acc(520, -900)
    amphitheatre(a2, 520, -900, CITY, 70)
    return [ac.build() for ac in accs.values()]


MOUNTAIN_MATS = set()


def horizon(rng):
    objs = []
    m = Acc("Mountains")
    for i in range(40):
        t = rng.uniform(-1.0, 1.0)
        r = rng.uniform(4200, 6200)
        c = Vector((math.sin(-t) * r, -math.cos(t) * r, 0))
        h = rng.uniform(150, 330)
        rx, ry = rng.uniform(900, 1600), rng.uniform(500, 900)
        col = T.rgbhex([a + (b - a) * rng.uniform(0.0, 0.35) for a, b in zip(T.hexrgb("8d7cb4"), T.hexrgb("b996b4"))])
        pts = [(c.x + math.cos(2 * math.pi * k / 7 + rng.uniform(-0.2, 0.2)) * rx, c.y + math.sin(2 * math.pi * k / 7) * ry, CITY - 5) for k in range(7)]
        peak = (c.x + rng.uniform(-150, 150), c.y + rng.uniform(-150, 150), CITY + h)
        mid = [((p[0] * 0.55 + peak[0] * 0.45), (p[1] * 0.55 + peak[1] * 0.45), CITY + h * rng.uniform(0.35, 0.55)) for p in pts]
        k1, k2 = m.key(col, 0.95), m.key(T.rgbhex([v * 1.07 for v in T.hexrgb(col)]), 0.95)
        for k in range(7):
            j = (k + 1) % 7
            m.poly([pts[k], pts[j], mid[j], mid[k]], k1)
            m.poly([mid[k], mid[j], peak], k2)
    mo = m.build()
    MOUNTAIN_MATS.update(ms.name for ms in mo.data.materials)
    objs.append(mo)
    # streaky faceted clouds: golden above, lavender below
    cl = Acc("Clouds")
    keys = [cl.key("ffd590", 0.9, 0, "ffca78", 1.7), cl.key("fbbb7e", 0.9, 0, "f8ac6c", 1.4), cl.key("f0a48a", 0.9, 0, "e89480", 1.1),
            cl.key("d098a6", 0.9, 0, "c48aa0", 0.9), cl.key("ae8cb6", 0.9, 0, "9c80ae", 0.8)]
    L = (Vector((0, 0, 1)) * 0.8 + Vector((SUN.x, SUN.y, 0)) * 0.5 + Vector((0, 1, 0)) * 0.3).normalized()
    for i in range(9):
        t = rng.uniform(-0.62, 0.62)
        d = rng.uniform(1100, 1900)
        elev = math.radians(rng.uniform(7, 21))
        c = Vector((math.sin(-t) * d, -math.cos(t) * d, H_CAM + d * math.tan(elev)))
        yaw = -t + rng.uniform(-0.45, 0.45)
        Lc = rng.uniform(380, 900)
        for k in range(rng.randint(3, 6)):
            u = (k / 5.0 - 0.5) * Lc
            cen = c + Vector((math.cos(yaw), math.sin(yaw), rng.uniform(-0.05, 0.05))) * u
            sx, sy, sz = rng.uniform(120, 220) * (1 - abs(u) / Lc * 0.6), rng.uniform(70, 130), rng.uniform(34, 70) * (1 - abs(u) / Lc * 0.5)
            segs, rings = 6, 3
            grid = []
            for r in range(rings + 1):
                ph = math.pi * r / rings
                row = []
                for q in range(segs):
                    th = 2 * math.pi * q / segs + (0.5 if r % 2 else 0)
                    v = Vector((math.sin(ph) * math.cos(th) * sx, math.sin(ph) * math.sin(th) * sy, max(math.cos(ph), -0.3) * sz))
                    v.rotate(Matrix.Rotation(yaw, 3, "Z"))
                    row.append(cen + v)
                grid.append(row)
            for r in range(rings):
                for q in range(segs):
                    qa, qb = q, (q + 1) % segs
                    for tri in ((grid[r][qa], grid[r + 1][qa], grid[r + 1][qb]), (grid[r][qa], grid[r + 1][qb], grid[r][qb])):
                        nrm = (tri[1] - tri[0]).cross(tri[2] - tri[0])
                        if nrm.length < 1e-6:
                            continue
                        nrm.normalize()
                        if nrm.dot(cen - (tri[0] + tri[1] + tri[2]) / 3) > 0:
                            nrm = -nrm
                        lit = nrm.dot(L)
                        idx = 0 if lit > 0.45 else 1 if lit > 0.1 else 2 if lit > -0.2 else 3 if lit > -0.5 else 4
                        cl.poly([tuple(p) for p in tri], keys[idx])
    objs.append(cl.build())
    s = Acc("Sun")
    sc = Vector((0, 0, H_CAM)) + SUN * 6000
    u = SUN.cross(Vector((0, 0, 1))).normalized()
    v = u.cross(SUN).normalized()
    for rad, key in ((52, s.key("fff2c8", 0.5, 0, "fff0b0", 40.0)), (95, s.key("ffd080", 0.5, 0, "ffc070", 6.0)), (240, s.key("ffa86a", 0.5, 0, "ffa068", 1.4))):
        s.poly([tuple(sc - SUN * rad * 0.02 + (u * math.cos(2 * math.pi * q / 20) + v * math.sin(2 * math.pi * q / 20)) * rad) for q in range(20)], key)
    objs.append(s.build())
    for o in objs:
        o.visible_shadow = False
    return objs


# ----------------------------------------------------------------------------- the balcony
def balcony(rng):
    a = Acc("Balcony")
    # floor: large marble slabs clipped to the balustrade line
    for i in range(-10, 16):
        for j in range(-8, 3):
            x0, y0 = i * 1.6 - 0.8, j * 1.6
            cxm = x0 + 0.8
            if y0 < bal_y(cxm) + 0.1:
                continue
            k = a.key("eadfd8" if (i + j) % 2 == 0 else "d6c8c0", 0.75)
            a.poly([(x0, y0, 0), (x0 + 1.6, y0, 0), (x0 + 1.6, y0 + 1.6, 0), (x0, y0 + 1.6, 0)], k)
    # the crimson carpet, diagonal toward the balustrade
    p0, p1 = Vector((3.2, 1.0)), Vector((1.2, -7.3))
    dvec = (p1 - p0).normalized()
    nvec = Vector((-dvec.y, dvec.x))
    for wdt, col, z in ((2.7, "c8862d", 0.012), (2.2, CRIMSON, 0.02)):
        q = [p0 + nvec * wdt / 2, p0 - nvec * wdt / 2, p1 - nvec * wdt / 2, p1 + nvec * wdt / 2]
        a.poly([(v.x, v.y, z) for v in q][::-1], a.key(col, 0.9))
    # the balustrade: chunky turned balusters between posts, a heavy rail, gold trim
    L = (BAL_L - BAL_R).length
    d = (BAL_L - BAL_R).normalized()
    yaw = math.atan2(d.y, d.x)
    mid = (BAL_R + BAL_L) / 2
    a.box((mid.x, mid.y, 0.13), (L + 1.0, 0.75, 0.26), a.key(MARBLE2), yaw)
    a.box((mid.x, mid.y, 1.02), (L + 1.0, 0.82, 0.2), a.key(MARBLE), yaw)
    a.box((mid.x, mid.y, 0.9), (L + 0.9, 0.66, 0.06), a.key(GOLD, 0.5, 0.4), yaw)
    n = int(L / 0.42)
    for k in range(n):
        p = BAL_R + d * (L * (k + 0.5) / n)
        if k % 7 == 3:
            a.box((p.x, p.y, 0.55), (0.62, 0.62, 0.92), a.key(MARBLE), yaw)
            continue
        a.stack([(0.26, ring(8, 0.1, 0.1), p.x, p.y), (0.44, ring(8, 0.18, 0.18), p.x, p.y), (0.58, ring(8, 0.12, 0.12), p.x, p.y),
                 (0.74, ring(8, 0.09, 0.09), p.x, p.y), (0.86, ring(8, 0.13, 0.13), p.x, p.y), (0.92, ring(8, 0.11, 0.11), p.x, p.y)], a.key("dccfba", 0.65))
    # cornice and wall falling away beyond it
    off = Vector((-d.y, d.x)) * -0.7
    a.box((mid.x + off.x, mid.y + off.y, -0.5), (L + 30, 1.4, 1.0), a.key(MARBLE), yaw)
    a.box((mid.x + off.x * 2, mid.y + off.y * 2, (CITY + 14) / 2 - 7), (L + 60, 2.0, -CITY - 14), a.key("d9c8a8"), yaw)
    # the palace loggia on the left: columns receding, an entablature, banners between
    cols = [(5.9, -8.3), (7.6, -9.4), (9.3, -10.5)]
    for (x, y) in cols:
        a.box((x, y, 0.25), (1.8, 1.8, 0.5), a.key(MARBLE2))
        a.stack([(0.5, ring(16, 0.68, 0.68, 0.04), x, y), (8.6, ring(16, 0.6, 0.6, 0.04), x, y)], a.key(MARBLE), False, False)
        a.stack([(8.6, ring(12, 0.66, 0.66), x, y), (8.95, ring(12, 0.82, 0.82), x, y)], a.key(GOLD, 0.5, 0.4))
        for s2 in (-1, 1):
            a.tube([(x - 0.85, y + s2 * 0.6, 9.15), (x + 0.85, y + s2 * 0.6, 9.15)], [0.27, 0.27], a.key(MARBLE), 8)
        a.box((x, y, 9.5), (2.1, 2.1, 0.4), a.key(MARBLE))
        a.box((x, y, 1.6), (1.5, 1.5, 0.12), a.key(GOLD, 0.5, 0.4))
    c0, c1 = Vector(cols[0]), Vector(cols[-1])
    cd = (c1 - c0)
    cyaw = math.atan2(cd.y, cd.x)
    cm = (c0 + c1) / 2
    a.box((cm.x, cm.y, 10.3), (cd.length + 2.4, 2.4, 1.2), a.key(MARBLE), cyaw)
    a.box((cm.x, cm.y, 11.05), (cd.length + 2.5, 2.5, 0.35), a.key(CRIMSON), cyaw)
    a.box((cm.x, cm.y, 11.5), (cd.length + 2.9, 2.9, 0.5), a.key(MARBLE), cyaw)
    a.box((cm.x + 6, cm.y + 4, 7.0), (cd.length + 4, 10, 14), a.key("e8d6ba"), cyaw)
    for k in range(len(cols) - 1):
        bm = (Vector(cols[k]) + Vector(cols[k + 1])) / 2
        banner_flat(a, (bm.x, bm.y + 0.2, 9.6), 1.3, 4.0, math.pi - 0.35)
    banner_flat(a, (4.9, -7.6, 9.4), 1.0, 3.6, math.pi - 0.35)
    # the statue's pedestal on the balustrade line, the banner pole by the fire
    sp = Vector((2.5, bal_y(2.5) + 0.55))
    a.box((sp.x, sp.y, 0.65), (1.5, 1.5, 1.3), a.key(MARBLE2))
    a.box((sp.x, sp.y, 1.35), (1.7, 1.7, 0.14), a.key(MARBLE))
    pole = Vector((-4.6, bal_y(-4.6) + 0.5))
    a.tube([(pole.x, pole.y, 0), (pole.x, pole.y, 6.8)], [0.08, 0.07], a.key(GOLD, 0.45, 0.5), 6)
    a.box((pole.x + 0.7, pole.y, 6.55), (1.9, 0.12, 0.12), a.key(GOLD, 0.45, 0.5))
    banner_flat(a, (pole.x + 0.75, pole.y + 0.1, 6.45), 1.0, 3.6, math.pi)
    a.T = Matrix.Identity(4)
    a.build()
    T.fire_bowl(-3.5, bal_y(-3.5) + 0.95, 0.9)
    T.statue_on(dict(C.CAST["thane"], headwear="none", prop="spear", cloak="x"), sp.x, sp.y, 1.42, 0.5, 1.55)


def court():
    who = [("emperor", (1.09, -6.0), 0.5, 1.3, dict(hair="4a2e1e", beard="full", prop="none")),
           ("herald", (3.0, -6.2), 0.75, 1.15, {}), ("treasurer", (4.2, -7.2), 0.9, 1.12, {}), ("chancellor", (4.6, -6.1), 1.3, 1.12, {}),
           ("aldric", (3.8, -5.4), 0.6, 1.12, {}), ("empress", (5.0, -7.8), 0.4, 1.12, {})]
    for cid, (x, y), yaw, sc, over in who:
        P.place(C.Figure(cid, dict(C.CAST[cid], **over)).build(), (x, y, 0.02), yaw, sc)


# ----------------------------------------------------------------------------- light, haze, camera
def apply_haze():
    """Aerial perspective in every opaque material: blend toward the haze colour with view distance."""
    hz = K.hexc(HAZE)
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.name in MOUNTAIN_MATS:
            continue
        nt = mat.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if out is None or bsdf is None or bsdf.inputs["Emission Strength"].default_value > 0.5:
            continue
        cam = nt.nodes.new("ShaderNodeCameraData")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 380.0
        mr.inputs["From Max"].default_value = 7000.0
        mr.inputs["To Min"].default_value = 0.0
        mr.inputs["To Max"].default_value = 1.0
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 0.85
        cl = nt.nodes.new("ShaderNodeMath")
        cl.operation = "MULTIPLY"
        cl.inputs[1].default_value = 0.8
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = hz
        em.inputs["Strength"].default_value = 1.0
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], pw.inputs[0])
        nt.links.new(pw.outputs["Value"], cl.inputs[0])
        nt.links.new(cl.outputs["Value"], mix.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(em.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


def lighting(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "Medium Contrast"
    except TypeError:
        pass
    w = bpy.data.worlds.new("Sunset")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = K.hexc("ffb868")
    cr.elements[1].position = 0.55
    cr.elements[1].color = K.hexc("4a3d8c")
    for pos, col in ((0.035, "ffa872"), (0.09, "f08e8a"), (0.18, "c68aa8"), (0.32, "8f76c0")):
        cr.elements.new(pos).color = K.hexc(col)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.95
    # key: a strong golden low sun from the right, long shadows toward the viewer's left
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
    sun = bpy.context.active_object
    sun.data.energy = 3.3
    sun.data.color = (1.0, 0.72, 0.44)
    sun.data.angle = math.radians(4.0)
    sun.rotation_euler = Vector((SUN.x, SUN.y, 0.2)).normalized().to_track_quat("Z", "Y").to_euler()
    # a soft warm sky-fill from behind and above, without shadows, so facing walls glow rather than go grey
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 60))
    fill = bpy.context.active_object
    fill.data.energy = 1.45
    fill.data.color = (1.0, 0.78, 0.62)
    fill.data.use_shadow = False
    fill.rotation_euler = Vector((-0.5, 0.8, 0.9)).normalized().to_track_quat("Z", "Y").to_euler()


def camera(res):
    sc = bpy.context.scene
    bpy.ops.object.camera_add(location=(0, 0, H_CAM))
    cam = bpy.context.active_object
    sc.camera = cam
    cam.rotation_euler = (math.pi / 2 + PITCH, 0, 0)
    cam.rotation_euler.z = 0.0
    # camera looks along -Y: rotate 180 degrees about Z
    cam.rotation_euler = (math.pi / 2 + PITCH, 0.0, math.pi)
    cam.data.lens = LENS
    cam.data.clip_end = 20000.0
    sc.render.resolution_x, sc.render.resolution_y = res
    return cam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--res", default="1672x941")
    ap.add_argument("--no-walkers", action="store_true")
    args = ap.parse_args()
    rng = random.Random(21)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    plan_city(rng)
    horizon(rng)
    balcony(rng)
    court()
    T.statue_on(dict(C.CAST["emperor"], prop="spear", cloak="x"), PLAZA.x, PLAZA.y, CITY + 7.5, 0.3, 3.2)
    if not args.no_walkers:
        T.WALKERS.clear()
        T.WALKERS.append(((PLAZA.x, PLAZA.y + 20), 40, 70, CITY + 0.2))
        T.WALKERS.append(((CAPITOL.x + 10, CAPITOL.y + 215), 18, 30, CITY))
        T.spawn_walkers(rng, 24, 100)
    lighting(args.samples)
    apply_haze()
    rx, ry = (int(v) for v in args.res.split("x"))
    camera((rx, ry))
    tris = sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type == "MESH")
    print("faces:", tris)
    out = os.path.join(ROOT, "renders", "vista.png")
    sc = bpy.context.scene
    sc.frame_set(1)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("render", out)


if __name__ == "__main__":
    main()
