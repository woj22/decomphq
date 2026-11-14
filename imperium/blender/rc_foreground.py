"""Stage 7: the foreground - marble terrace, balustrade, Ionic loggia, banners, statue, brazier, court.

Placement follows the reference: columns and laurel banners far left, the spear statue on its pedestal
on the left (well above human scale), the burgundy-cloaked ruler centre-foreground seen from behind with
robed attendants beside him, the brazier and a hanging banner far right.
"""
import math

import bpy
from mathutils import Matrix, Vector

import rc_common as R
import cast as C
import palace as P
import city as T
from city import Acc, ring
import vista as V

MARBLE, MARBLE2, GOLD, CRIMSON = T.MARBLE, T.MARBLE2, T.GOLD, T.CRIMSON
STATUE_SCALE = 1.6           # about 1.4x the court (people are 1.1-1.3), as in the reference


def fluted(n, r, depth=0.06):
    """A fluted column cross-section: 2n vertices alternating between the arris and the flute."""
    return [(math.cos(2 * math.pi * k / (2 * n)) * r * (1 - (depth if k % 2 else 0)),
             math.sin(2 * math.pi * k / (2 * n)) * r * (1 - (depth if k % 2 else 0))) for k in range(2 * n)]


def ionic(a, x, y, h, r, yaw=0.0):
    """An Ionic column: plinth, torus/scotia base, fluted tapering shaft, echinus, scrolled volutes, abacus."""
    m, g = a.key(MARBLE), a.key(GOLD, 0.5, 0.4)
    a.box((x, y, 0.18 * r / 0.6), (r * 3.0, r * 3.0, 0.36 * r / 0.6), a.key(MARBLE2), yaw)
    z = 0.36 * r / 0.6
    a.stack([(z, ring(16, r * 1.35, r * 1.35), x, y), (z + 0.12, ring(16, r * 1.42, r * 1.42), x, y), (z + 0.24, ring(16, r * 1.2, r * 1.2), x, y),
             (z + 0.3, ring(16, r * 1.1, r * 1.1), x, y), (z + 0.4, ring(16, r * 1.2, r * 1.2), x, y), (z + 0.5, ring(16, r * 1.05, r * 1.05), x, y)], m)
    z0 = z + 0.5
    zc = h - 0.9 * r / 0.6
    a.stack([(z0, fluted(12, r), x, y), (z0 + (zc - z0) * 0.35, fluted(12, r * 0.98), x, y), (zc, fluted(12, r * 0.86), x, y)], m, False, False)
    a.stack([(zc, ring(16, r * 0.9, r * 0.9), x, y), (zc + 0.1, ring(16, r * 0.98, r * 0.98), x, y), (zc + 0.16, ring(16, r * 0.9, r * 0.9), x, y)], g)
    a.stack([(zc + 0.16, ring(16, r * 0.92, r * 0.92), x, y), (zc + 0.42, ring(16, r * 1.18, r * 1.18), x, y)], m)
    c, s = math.cos(yaw), math.sin(yaw)
    for side in (-1, 1):
        for face in (-1, 1):      # a scroll on each face, either side: a spiralling tube
            pts, rad = [], []
            for k in range(14):
                t = k / 13 * 2.4 * math.pi
                rr = r * 0.38 * (1 - k / 16)
                u = side * (r * 1.12 + math.cos(t) * rr * side)
                v = zc + 0.3 - r * 0.15 + math.sin(t) * rr
                w = face * r * 0.75
                pts.append((x + c * u - s * w, y + s * u + c * w, v))
                rad.append(r * 0.1 * (1 - k / 20))
            a.tube(pts, rad, m, 6)
        a.box((x + c * side * r * 1.0, y + s * side * r * 1.0, zc + 0.35), (r * 0.5, r * 1.5, r * 0.36), m, yaw)
    a.box((x, y, zc + 0.56), (r * 2.9, r * 2.9, 0.24), m, yaw)
    a.box((x, y, zc + 0.7), (r * 3.05, r * 3.05, 0.06), g, yaw)


def floor(a):
    """Geometric marble paving: large bordered squares each holding an inset diamond, set diagonally
    to the balustrade so the pattern carries the eye toward the city."""
    S = 2.0
    k1, k2, k3, k4 = a.key("e6dace", 0.92), a.key("d2c2b4", 0.92), a.key("c2a288", 0.92), a.key("b08466", 0.9)
    for i in range(-8, 12):
        for j in range(-7, 3):
            x0, y0 = i * S - 1.0, j * S
            if y0 < V.bal_y(x0 + S / 2) + 0.1:
                continue
            cx, cy = x0 + S / 2, y0 + S / 2
            # border band, field, diamond, tiny centre stone
            a.poly([(x0, y0, 0), (x0 + S, y0, 0), (x0 + S, y0 + S, 0), (x0, y0 + S, 0)], k2 if (i + j) % 2 else k3)
            b = 0.16
            a.poly([(x0 + b, y0 + b, 0.004), (x0 + S - b, y0 + b, 0.004), (x0 + S - b, y0 + S - b, 0.004), (x0 + b, y0 + S - b, 0.004)], k1)
            d = S / 2 - b - 0.05
            a.poly([(cx, cy - d, 0.008), (cx + d, cy, 0.008), (cx, cy + d, 0.008), (cx - d, cy, 0.008)], k2 if (i + j) % 2 else k1)
            e = 0.2
            a.poly([(cx, cy - e, 0.012), (cx + e, cy, 0.012), (cx, cy + e, 0.012), (cx - e, cy, 0.012)], k4)


def build_foreground():
    R.clear("Foreground")
    R.clear("Characters")
    before = set(bpy.data.objects)
    a = Acc("Balcony")
    floor(a)
    # crimson carpet with gold borders running toward the balustrade
    p0, p1 = Vector((3.2, 1.0)), Vector((1.2, -7.3))
    dv = (p1 - p0).normalized()
    nv = Vector((-dv.y, dv.x))
    for wdt, col, z in ((2.8, "c8862d", 0.016), (2.5, CRIMSON, 0.02), (1.9, "c8862d", 0.022), (1.8, CRIMSON, 0.024)):
        q = [p0 + nv * wdt / 2, p0 - nv * wdt / 2, p1 - nv * wdt / 2, p1 + nv * wdt / 2]
        a.poly([(v.x, v.y, z) for v in q][::-1], a.key(col, 0.9))
    # balustrade
    BR, BL = V.BAL_R, V.BAL_L
    L = (BL - BR).length
    d = (BL - BR).normalized()
    yaw = math.atan2(d.y, d.x)
    mid = (BR + BL) / 2
    a.box((mid.x, mid.y, 0.13), (L + 1.0, 0.75, 0.26), a.key(MARBLE2), yaw)
    a.box((mid.x, mid.y, 1.02), (L + 1.0, 0.82, 0.2), a.key(MARBLE), yaw)
    a.box((mid.x, mid.y, 0.9), (L + 0.9, 0.66, 0.06), a.key(GOLD, 0.5, 0.4), yaw)
    n = int(L / 0.42)
    for k in range(n):
        p = BR + d * (L * (k + 0.5) / n)
        if k % 7 == 3:
            a.box((p.x, p.y, 0.55), (0.62, 0.62, 0.92), a.key(MARBLE), yaw)
            continue
        a.stack([(0.26, ring(8, 0.1, 0.1), p.x, p.y), (0.44, ring(8, 0.18, 0.18), p.x, p.y), (0.58, ring(8, 0.12, 0.12), p.x, p.y),
                 (0.74, ring(8, 0.09, 0.09), p.x, p.y), (0.86, ring(8, 0.13, 0.13), p.x, p.y), (0.92, ring(8, 0.11, 0.11), p.x, p.y)], a.key("dccfba", 0.65))
    off = Vector((-d.y, d.x)) * -0.7
    a.box((mid.x + off.x, mid.y + off.y, -0.5), (L + 30, 1.4, 1.0), a.key(MARBLE), yaw)
    a.box((mid.x + off.x * 2, mid.y + off.y * 2, -20.0), (L + 60, 2.0, 38.0), a.key("d9c8a8"), yaw)
    # the Ionic loggia far left, with its entablature and laurel banners
    cols = [(5.9, -8.3), (7.6, -9.4), (9.3, -10.5)]
    for (x, y) in cols:
        ionic(a, x, y, 6.2, 0.5, math.radians(-33))
    c0, c1 = Vector(cols[0]), Vector(cols[-1])
    cd = c1 - c0
    cyaw = math.atan2(cd.y, cd.x)
    cm = (c0 + c1) / 2
    a.box((cm.x, cm.y, 7.1), (cd.length + 2.4, 2.4, 1.0), a.key(MARBLE), cyaw)
    a.box((cm.x, cm.y, 7.75), (cd.length + 2.5, 2.5, 0.3), a.key(GOLD, 0.5, 0.4), cyaw)
    a.box((cm.x, cm.y, 8.2), (cd.length + 2.6, 2.6, 0.6), a.key(CRIMSON), cyaw)
    a.box((cm.x, cm.y, 8.7), (cd.length + 3.0, 3.0, 0.4), a.key(MARBLE), cyaw)
    for k in range(9):          # dentils under the cornice
        p = c0 + cd * (k / 8)
        a.box((p.x, p.y, 8.45), (0.3, 3.05, 0.2), a.key(MARBLE2), cyaw)
    a.box((cm.x + 6, cm.y + 4, 7.0), (cd.length + 4, 10, 14), a.key("e8d6ba"), cyaw)
    for k in range(len(cols) - 1):
        bm = (Vector(cols[k]) + Vector(cols[k + 1])) / 2
        T.banner_flat(a, (bm.x, bm.y + 0.2, 6.6), 1.2, 3.4, math.pi - 0.35)
    T.banner_flat(a, (4.9, -7.6, 6.5), 1.0, 3.2, math.pi - 0.35)
    # statue pedestal: moulded plinth with a gold band
    sp = Vector((2.5, V.bal_y(2.5) + 0.55))
    a.box((sp.x, sp.y, 0.12), (1.9, 1.9, 0.24), a.key(MARBLE))
    a.box((sp.x, sp.y, 0.7), (1.55, 1.55, 1.0), a.key(MARBLE2))
    a.box((sp.x, sp.y, 1.0), (1.6, 1.6, 0.08), a.key(GOLD, 0.5, 0.4))
    a.box((sp.x, sp.y, 1.3), (1.8, 1.8, 0.16), a.key(MARBLE))
    # the hanging banner far right, on a gilded bracket
    pole = Vector((-4.6, V.bal_y(-4.6) + 0.5))
    a.tube([(pole.x, pole.y, 0), (pole.x, pole.y, 6.8)], [0.09, 0.07], a.key(GOLD, 0.45, 0.5), 6)
    a.cone((pole.x, pole.y, 6.8), 0.16, 0.4, a.key(GOLD, 0.45, 0.5), 6)
    a.box((pole.x + 0.7, pole.y, 6.55), (1.9, 0.12, 0.12), a.key(GOLD, 0.45, 0.5))
    T.banner_flat(a, (pole.x + 0.75, pole.y + 0.1, 6.45), 1.0, 3.6, math.pi)
    a.T = Matrix.Identity(4)
    a.build()
    T.fire_bowl(-3.5, V.bal_y(-3.5) + 0.95, 0.9)
    T.statue_on(dict(C.CAST["thane"], headwear="none", prop="spear", cloak="x"), sp.x, sp.y, 1.38, 0.5, STATUE_SCALE)
    for o in set(bpy.data.objects) - before:
        R.move_to(o, "Foreground")
    before = set(bpy.data.objects)
    who = [("emperor", (1.09, -6.0), 0.5, 1.3, dict(hair="4a2e1e", beard="full", prop="none", royal=True)),
           ("herald", (3.0, -6.2), 0.75, 1.15, {}), ("treasurer", (4.2, -7.2), 0.9, 1.12, {}), ("chancellor", (4.6, -6.1), 1.3, 1.12, {}),
           ("aldric", (3.8, -5.4), 0.6, 1.12, {}), ("empress", (5.0, -7.8), 0.4, 1.12, {})]
    for cid, (x, y), yw, sc, over in who:
        P.place(C.Figure(cid, dict(C.CAST[cid], **over)).build(), (x, y, 0.02), yw, sc)
    for o in set(bpy.data.objects) - before:
        R.move_to(o, "Characters")
