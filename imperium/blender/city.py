"""The Imperial Balcony and the city of Caelora below it, hand-placed low-poly.

Run:  python3 imperium/blender/city.py [--samples N] [--only shot]
Writes renders/balcony_*.png.

Everything outside the balcony goes through `Acc`, a mesh accumulator: thousands of buildings are
written into a few large meshes (one per material set), so the city can be dense and detailed.
Distance haze is baked into the colours (materials are keyed by colour and haze band).
Layout: the balcony is at z=0, looking toward -Y over the city at z=-24; the sun sets ahead and right.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

import kharad as K  # noqa: E402
import cast as C  # noqa: E402
import palace as P  # noqa: E402

ROOT = K.ROOT
CITY_Z = -26.0
SUN_DIR = Vector((-0.36, -1.0, 0.085)).normalized()     # from the scene toward the sun
HAZE = (0.86, 0.66, 0.66)                              # lavender-peach evening haze (linear-ish target)
CAM = Vector((0.0, 7.5, 3.0))

MARBLE, MARBLE2, MARBLE3 = "ece4d4", "d6cab4", "bcae96"
ROOF, ROOF2 = "b04e36", "9a4230"
GOLD, CRIMSON = "c8862d", "8e1f24"
WALLS = ["f2e6d0", "ecdcc0", "f5ecdc", "e6cfac", "efe0c6", "e9d6bc", "f3e4cc", "e2c4a0"]
TREE, PINE = "3e5a32", "4f6a38"
DARK = "4a3238"


def hexrgb(h):
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def rgbhex(c):
    return "%02x%02x%02x" % tuple(max(0, min(255, int(round(v * 255)))) for v in c)


class Acc:
    """Accumulates flat-shaded geometry with per-face materials into one mesh."""

    def __init__(self, name):
        self.name = name
        self.v, self.f, self.mi = [], [], []
        self.keys = {}
        self.T = Matrix.Identity(4)
        self.haze = 0.0

    def key(self, hexcol, rough=0.85, metal=0.0, emit=None, strength=0.0):
        if self.haze > 0 and not emit:
            c = hexrgb(hexcol)
            hz = [0.84, 0.69, 0.7]
            k = min(0.75, self.haze)
            hexcol = rgbhex([a + (b - a) * k for a, b in zip(c, hz)])
            hexcol = rgbhex([round(x * 24) / 24 for x in hexrgb(hexcol)])   # quantise to share materials
        k2 = (hexcol, round(rough, 1), round(metal, 1), emit, strength)
        if k2 not in self.keys:
            self.keys[k2] = len(self.keys)
        return self.keys[k2]

    def poly(self, pts, mat):
        b = len(self.v)
        self.v += [tuple(self.T @ Vector(p)) for p in pts]
        self.f.append(tuple(range(b, b + len(pts))))
        self.mi.append(mat)

    def box(self, c, size, mat, yaw=0.0, taper=1.0):
        cx, cy, cz = c
        sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
        R = Matrix.Rotation(yaw, 3, "Z")
        pts = []
        for z, k in ((-sz, 1.0), (sz, taper)):
            pts += [Vector((-sx * k, -sy * k, z)), Vector((sx * k, -sy * k, z)), Vector((sx * k, sy * k, z)), Vector((-sx * k, sy * k, z))]
        pts = [R @ p + Vector((cx, cy, cz)) for p in pts]
        for fa in ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.poly([pts[i] for i in fa], mat)

    def stack(self, sections, mat, cap_bottom=True, cap_top=True):
        n = len(sections[0][1])
        rings = [[(cx + x, cy + y, z) for (x, y) in pts] for (z, pts, cx, cy) in sections]
        for a, b in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                self.poly([a[i], a[j], b[j], b[i]], mat)
        if cap_bottom:
            self.poly(list(reversed(rings[0])), mat)
        if cap_top:
            self.poly(rings[-1], mat)

    def tube(self, path, radii, mat, sides=6):
        pts = [Vector(p) for p in path]
        rings = []
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            ref = Vector((0, -1, 0)) if abs(t.y) < 0.9 else Vector((1, 0, 0))
            u = (ref - t * ref.dot(t)).normalized()
            v = t.cross(u).normalized()
            rings.append([p + (u * math.cos(2 * math.pi * i / sides) + v * math.sin(2 * math.pi * i / sides)) * radii[k] for i in range(sides)])
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                self.poly([a[i], a[j], b[j], b[i]], mat)
        self.poly(list(reversed(rings[0])), mat)
        if radii[-1] > 0.001:
            self.poly(rings[-1], mat)

    def cone(self, base, r, h, mat, sides=6):
        b = Vector(base)
        ring = [b + Vector((math.cos(2 * math.pi * i / sides) * r, math.sin(2 * math.pi * i / sides) * r, 0)) for i in range(sides)]
        tip = b + Vector((0, 0, h))
        for i in range(sides):
            self.poly([ring[i], ring[(i + 1) % sides], tip], mat)
        self.poly(list(reversed(ring)), mat)

    def build(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        mats = [None] * len(self.keys)
        for k, i in self.keys.items():
            mats[i] = C.m(k[0], k[1], k[2], k[3], k[4])
        for mm in mats:
            me.materials.append(mm)
        me.polygons.foreach_set("material_index", self.mi)
        me.polygons.foreach_set("use_smooth", [False] * len(self.f))
        ca = me.color_attributes.new("facet", "BYTE_COLOR", "CORNER")
        ca.data.foreach_set("color", [1.0] * (4 * len(ca.data)))
        o = bpy.data.objects.new(self.name, me)
        bpy.context.collection.objects.link(o)
        return o


def ring(n, rx, ry, fold=0.0, phase=0.0):
    return [(math.cos(phase + 2 * math.pi * i / n) * rx * (1 + (fold if i % 2 else -fold)),
             math.sin(phase + 2 * math.pi * i / n) * ry * (1 + (fold if i % 2 else -fold))) for i in range(n)]


def at(acc, x, y, z, yaw):
    acc.T = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z")


# ----------------------------------------------------------------------------- facade details
def facade_openings(a, w, d, h_floor, floors, side, mats, rng, arcade):
    """Windows (framed, recessed-dark) and a ground-floor arcade on one facade (local coords).
    side: 0=-Y (front), 1=+X, 2=+Y, 3=-X."""
    length = w if side in (0, 2) else d
    n = max(1, int(length / 2.7))
    step = length / n
    def pt(u, z, out=0.03):
        # u along the facade (centred), z height; facades lie on the box faces
        if side == 0:
            return (u, -d / 2 - out, z)
        if side == 2:
            return (-u, d / 2 + out, z)
        if side == 1:
            return (w / 2 + out, u, z)
        return (-w / 2 - out, -u, z)
    for f in range(floors):
        for i in range(n):
            u = -length / 2 + step * (i + 0.5)
            if f == 0:
                if arcade:
                    # arched shop opening with a marble archivolt
                    aw, ah = min(2.2, step * 0.72), 2.4
                    seg = 6
                    arc = [pt(u + math.cos(math.pi * k / seg) * aw / 2, ah - aw / 2 + math.sin(math.pi * k / seg) * aw / 2, 0.04) for k in range(seg + 1)]
                    outline = [pt(u + aw / 2, 0.02, 0.04)] + arc + [pt(u - aw / 2, 0.02, 0.04)]
                    a.poly(outline, mats["dark"])
                    arc2 = [pt(u + math.cos(math.pi * k / seg) * (aw / 2 + 0.22), ah - aw / 2 + math.sin(math.pi * k / seg) * (aw / 2 + 0.22), 0.025) for k in range(seg + 1)]
                    for k in range(seg):
                        a.poly([arc[k], arc[k + 1], arc2[k + 1], arc2[k]][::-1] if side in (0, 1, 2, 3) else [], mats["trim"])
                elif rng.random() < 0.35:
                    dw, dh = 1.3, 2.3
                    a.poly([pt(u - dw / 2, 0.02, 0.04), pt(u + dw / 2, 0.02, 0.04), pt(u + dw / 2, dh, 0.04), pt(u - dw / 2, dh, 0.04)], mats["door"])
                continue
            z0 = f * h_floor + 0.9
            ww, wh = 0.85, 1.35
            a.poly([pt(u - ww / 2 - 0.14, z0 - 0.16, 0.02), pt(u + ww / 2 + 0.14, z0 - 0.16, 0.02), pt(u + ww / 2 + 0.14, z0 + wh + 0.12, 0.02), pt(u - ww / 2 - 0.14, z0 + wh + 0.12, 0.02)], mats["trim"])
            a.poly([pt(u - ww / 2, z0, 0.045), pt(u + ww / 2, z0, 0.045), pt(u + ww / 2, z0 + wh, 0.045), pt(u - ww / 2, z0 + wh, 0.045)], mats["dark"])


def facade_grand(a, w, d, hf, floors, side, mats, rng, style):
    """Pilasters, arched framed windows, an arcade, and (front only) a loggia, a temple-front portico or a banner."""
    L = w if side in (0, 2) else d
    H = floors * hf + 0.5
    n = max(2, int(L / 3.3))
    step = L / n
    def pt(u, z, out):
        if side == 0:
            return (u, -d / 2 - out, z)
        if side == 2:
            return (-u, d / 2 + out, z)
        if side == 1:
            return (w / 2 + out, u, z)
        return (-w / 2 - out, -u, z)
    def slab(u, z, du, dz, out, depth, mat):
        c = pt(u, z, out)
        sz = (du, depth, dz) if side in (0, 2) else (depth, du, dz)
        a.box(c, sz, mat)
    for i in range(n + 1):
        slab(-L / 2 + i * step, H / 2, 0.42, H - 0.9, 0.08, 0.16, mats["trim"])
    seg = 5
    def arch_poly(u, z0, ww, wh, out, mat):
        pts = [pt(u - ww / 2, z0, out), pt(u + ww / 2, z0, out)]
        for k in range(seg + 1):
            ang = math.pi * k / seg
            pts.append(pt(u + math.cos(ang) * ww / 2, z0 + wh + math.sin(ang) * ww / 2, out))
        a.poly(pts, mat)
    for f in range(floors):
        for i in range(n):
            u = -L / 2 + step * (i + 0.5)
            if f == 0:
                if style.get("arcade"):
                    arch_poly(u, 0.02, min(2.4, step * 0.7) + 0.4, 1.7, 0.03, mats["trim"])
                    arch_poly(u, 0.02, min(2.4, step * 0.7), 1.7, 0.05, mats["dark"])
                elif i == n // 2:
                    arch_poly(u, 0.02, 1.6, 1.8, 0.05, mats["door"])
                continue
            if style.get("loggia") and side == 2 and f == floors - 1:
                continue
            z0 = f * hf + 0.75
            arch_poly(u, z0 - 0.12, 1.25, 1.05, 0.03, mats["trim"])
            arch_poly(u, z0, 0.95, 1.0, 0.05, mats["dark"])
            slab(u, z0 - 0.16, 1.4, 0.1, 0.12, 0.22, mats["trim"])
    if side != 2:
        return
    if style.get("loggia"):
        z0 = (floors - 1) * hf + 0.1
        a.poly([pt(-L / 2 + 0.3, z0, 0.04), pt(L / 2 - 0.3, z0, 0.04), pt(L / 2 - 0.3, z0 + hf - 0.2, 0.04), pt(-L / 2 + 0.3, z0 + hf - 0.2, 0.04)], mats["shade"])
        for i in range(n * 2 + 1):
            u = -L / 2 + 0.4 + (L - 0.8) * i / (n * 2)
            c0, c1 = pt(u, z0, 0.35), pt(u, z0 + hf - 0.25, 0.35)
            a.tube([c0, c1], [0.16, 0.14], mats["trim"], 8)
        slab(0, z0, L, 0.18, 0.35, 0.8, mats["trim"])
    if style.get("portico") and floors >= 2:
        ph = min(floors, 3) * hf
        pw = min(L * 0.6, 12.0)
        nc = 4 if pw < 9 else 6
        for i in range(nc):
            u = -pw / 2 + pw * i / (nc - 1)
            a.tube([pt(u, 0.3, 2.2), pt(u, ph - 0.6, 2.2)], [0.36, 0.3], mats["trim"], 10)
            slab(u, 0.15, 0.9, 0.3, 2.2, 0.9, mats["trim"])
        slab(0, ph - 0.3, pw + 1.0, 0.6, 1.2, 2.6, mats["trim"])
        slab(0, ph + 0.1, pw + 1.1, 0.25, 1.2, 2.7, mats["frieze"])
        tri = [pt(-pw / 2 - 0.5, ph + 0.25, 2.5), pt(pw / 2 + 0.5, ph + 0.25, 2.5), pt(0, ph + 0.25 + pw * 0.22, 2.5)]
        a.poly(tri, mats["trim"])
        a.poly([pt(-pw / 2 - 0.5, ph + 0.25, 2.5), pt(-pw / 2 - 0.5, ph + 0.25, -0.1), pt(0, ph + 0.25 + pw * 0.22, -0.1), pt(0, ph + 0.25 + pw * 0.22, 2.5)], mats["roof"])
        a.poly([pt(pw / 2 + 0.5, ph + 0.25, -0.1), pt(pw / 2 + 0.5, ph + 0.25, 2.5), pt(0, ph + 0.25 + pw * 0.22, 2.5), pt(0, ph + 0.25 + pw * 0.22, -0.1)], mats["roof"])
    if style.get("banner"):
        yaw = {0: 0.0, 1: math.pi / 2, 2: math.pi, 3: -math.pi / 2}[side]
        for u in ((-step, step) if n >= 3 else (0,)):
            banner_flat(a, pt(u, H - 0.9, 0.25), 1.4, min(H * 0.55, 6.0), yaw)


def arcade_wall(a, x0, x1, y, z0, h, skip=None):
    """A terrace retaining wall facing +Y: pilasters, arched dark recesses, a balustrade on top."""
    mm, m2, dk = a.key(MARBLE), a.key("e2d6c0"), a.key("6a4c44")
    a.box(((x0 + x1) / 2, y - 0.4, z0 + h / 2), (x1 - x0, 0.8, h), m2)
    n = int((x1 - x0) / 6.5)
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        if skip and skip[0] < x < skip[1]:
            continue
        aw, ah = 3.4, h * 0.42
        pts = [(x - aw / 2, y + 0.02, z0 + 0.3), (x + aw / 2, y + 0.02, z0 + 0.3)]
        for k in range(7):
            ang = math.pi * k / 6
            pts.append((x + math.cos(ang) * aw / 2, y + 0.02, z0 + 0.3 + ah + math.sin(ang) * aw / 2))
        a.poly(pts, dk)
        a.box((x - (x1 - x0) / n / 2, y + 0.15, z0 + h / 2), (0.7, 0.3, h), mm)
    a.box(((x0 + x1) / 2, y + 0.2, z0 + h - 0.3), (x1 - x0, 0.5, 0.6), mm)
    for k in range(int((x1 - x0) / 0.9)):
        x = x0 + 0.45 + k * 0.9
        if skip and skip[0] < x < skip[1]:
            continue
        a.box((x, y - 0.2, z0 + h + 0.45), (0.25, 0.25, 0.9), mm)
    a.box(((x0 + x1) / 2, y - 0.2, z0 + h + 0.95), (x1 - x0, 0.4, 0.2), mm)


def hip_roof(a, w, d, z, mat, ridge_mat, overhang=0.6, rise_k=0.32):
    w2, d2 = w + overhang * 2, d + overhang * 2
    rise = min(w, d) * rise_k
    if w >= d:
        r0, r1 = Vector((-(w2 - d2) / 2, 0, z + rise)), Vector(((w2 - d2) / 2, 0, z + rise))
    else:
        r0, r1 = Vector((0, -(d2 - w2) / 2, z + rise)), Vector((0, (d2 - w2) / 2, z + rise))
    c = [Vector((-w2 / 2, -d2 / 2, z)), Vector((w2 / 2, -d2 / 2, z)), Vector((w2 / 2, d2 / 2, z)), Vector((-w2 / 2, d2 / 2, z))]
    if w >= d:
        a.poly([c[0], c[1], r1, r0], mat)
        a.poly([c[2], c[3], r0, r1], mat)
        a.poly([c[1], c[2], r1], mat)
        a.poly([c[3], c[0], r0], mat)
    else:
        a.poly([c[1], c[2], r1, r0], mat)
        a.poly([c[3], c[0], r0, r1], mat)
        a.poly([c[0], c[1], r0], mat)
        a.poly([c[2], c[3], r1], mat)
    a.poly(list(reversed(c)), mat)
    a.tube([tuple(r0), tuple(r1)], [0.14, 0.14], ridge_mat, 4)


NEAR = 260.0


def insula(a, w, d, floors, rng, detail, near=False):
    wall = WALLS[rng.randrange(len(WALLS))]
    mats = {"wall": a.key(wall), "trim": a.key(MARBLE), "dark": a.key("5e4038", 0.9), "door": a.key("6a4430"), "shade": a.key("8a6a5e"),
            "frieze": a.key(CRIMSON), "roof": a.key(ROOF if rng.random() < 0.7 else ROOF2), "ridge": a.key("8a3a28"), "plinth": a.key(MARBLE2)}
    hf = 3.2
    H = floors * hf + 0.5
    a.box((0, 0, H / 2), (w, d, H), mats["wall"])
    a.box((0, 0, 0.35), (w + 0.12, d + 0.12, 0.7), mats["plinth"])
    for f in range(1, floors):
        a.box((0, 0, f * hf + 0.05), (w + 0.14, d + 0.14, 0.16), mats["trim"])
    a.box((0, 0, H - 0.1), (w + 0.4, d + 0.4, 0.3), mats["trim"])
    if detail:
        style = {"arcade": rng.random() < 0.6, "loggia": floors >= 3 and rng.random() < 0.5,
                 "portico": rng.random() < 0.3, "banner": rng.random() < 0.4}
        for side in (2, 1, 3):
            facade_grand(a, w, d, hf, floors, side, mats, rng, style if side == 2 else {"arcade": style["arcade"]})
        if floors >= 2 and rng.random() < 0.3:
            # a wooden balcony on the first floor
            bw = min(w * 0.6, 5.0)
            a.box((0, -d / 2 - 0.45, hf + 0.1), (bw, 0.9, 0.12), a.key("6b4a2e"))
            for k in range(int(bw / 0.5) + 1):
                a.box((-bw / 2 + k * 0.5, -d / 2 - 0.88, hf + 0.55), (0.06, 0.06, 0.9), a.key("6b4a2e"))
            a.box((0, -d / 2 - 0.88, hf + 1.0), (bw, 0.08, 0.08), a.key("6b4a2e"))
    if near and rng.random() < 0.55:
        # a flat roof terrace with a balustrade, plants and sometimes an awning
        a.box((0, 0, H + 0.05), (w, d, 0.1), a.key("d9c7aa"))
        for k in range(int((w + d) * 2 / 0.9)):
            t = k * 0.9
            if t < w:
                px, py = -w / 2 + t, d / 2
            elif t < w + d:
                px, py = w / 2, d / 2 - (t - w)
            elif t < 2 * w + d:
                px, py = w / 2 - (t - w - d), -d / 2
            else:
                px, py = -w / 2, -d / 2 + (t - 2 * w - d)
            a.box((px, py, H + 0.5), (0.22, 0.22, 0.8), mats["trim"])
        for k in range(rng.randint(1, 3)):
            tree(a, (rng.uniform(-w / 3, w / 3), rng.uniform(-d / 3, d / 3), H + 0.1), rng.uniform(3, 5), rng.choice(("cypress", "pine")))
    elif rng.random() < 0.15 and detail:
        # roof garden with a pergola and potted trees
        a.box((0, 0, H + 0.05), (w, d, 0.1), a.key("c9b293"))
        for k in range(4):
            px, py = (-w / 4 if k % 2 else w / 4), (-d / 4 if k < 2 else d / 4)
            a.tube([(px, py, H), (px, py, H + 2.4)], [0.08, 0.08], a.key("6b4a2e"), 4)
        a.box((0, 0, H + 2.45), (w * 0.6, d * 0.6, 0.12), a.key("6b4a2e"))
        a.box((0, 0, H + 2.6), (w * 0.55, d * 0.55, 0.25), a.key(PINE))
        a.box((0, 0, H + 0.95), (w + 0.1, d + 0.1, 0.08), mats["trim"])
    else:
        hip_roof(a, w, d, H, mats["roof"], mats["ridge"], 0.55, rng.uniform(0.25, 0.36))
    return H


def domus(a, s, rng, detail):
    """A courtyard house: four tiled wings sloping inward around a garden."""
    wall = WALLS[rng.randrange(len(WALLS))]
    mw, mr, mt = a.key(wall), a.key(ROOF), a.key(MARBLE)
    h = 4.2
    t = s * 0.28
    for (cx, cy, w, d, inward) in ((0, -s / 2 + t / 2, s, t, (0, 1)), (0, s / 2 - t / 2, s, t, (0, -1)), (-s / 2 + t / 2, 0, t, s - 2 * t, (1, 0)), (s / 2 - t / 2, 0, t, s - 2 * t, (-1, 0))):
        a.box((cx, cy, h / 2), (w, d, h), mw)
        a.box((cx, cy, h - 0.1), (w + 0.25, d + 0.25, 0.22), mt)
        # roof sloping into the court
        ix, iy = inward
        hw, hd = w / 2 + 0.4, d / 2 + 0.4
        hi = 1.6
        if iy:
            outer = cy - iy * hd
            inner = cy + iy * hd
            a.poly([(cx - hw, outer, h + hi), (cx + hw, outer, h + hi), (cx + hw, inner, h), (cx - hw, inner, h)][::(1 if iy > 0 else -1)], mr)
        else:
            outer = cx - ix * hw
            inner = cx + ix * hw
            a.poly([(outer, cy - hd, h + hi), (outer, cy + hd, h + hi), (inner, cy + hd, h), (inner, cy - hd, h)][::(-1 if ix > 0 else 1)], mr)
    a.box((0, 0, 0.15), (s - 2 * t, s - 2 * t, 0.3), a.key("6f8f45"))
    a.box((0, 0, 0.35), (1.2, 1.2, 0.4), a.key("6a9ec0"))
    tree(a, (s * 0.18, s * 0.12, 0.3), 5.5, "cypress")
    if detail:
        mats = {"wall": mw, "trim": mt, "dark": a.key("3e2c30", 0.9), "door": a.key("5a3a26")}
        facade_openings(a, s, s, 4.0, 1, 0, mats, rng, False)


def temple(a, w, d, colh, rng=None, front_banners=False, gold_roof=False):
    """A peripteral temple in local coordinates, front facing -Y."""
    mm, m2, mr, mg, mc = a.key(MARBLE), a.key(MARBLE2), a.key(ROOF if not gold_roof else "c99a45", 0.6, 0.4 if gold_roof else 0.0), a.key(GOLD, 0.5, 0.4), a.key(CRIMSON)
    pod = 2.0
    a.box((0, 0, pod / 2), (w + 2.4, d + 2.4, pod), m2)
    a.box((0, 0, pod - 0.1), (w + 2.6, d + 2.6, 0.2), mm)
    nst = 8
    for i in range(nst):
        a.box((0, -d / 2 - 1.2 - (nst - i) * 0.45 + 0.225, pod * (i + 1) / nst / 2), (w * 0.85, 0.45, pod * (i + 1) / nst), mm)
    a.box((0, d * 0.08, pod + colh / 2), (w - 2.6, d * 0.72, colh), a.key("efe3cf"))
    a.box((0, -d * 0.28 - 0.01, pod + colh * 0.42), (2.0, 0.1, colh * 0.8), a.key("3a2a28"))
    r = colh * 0.07
    nf = max(4, int(round((w - 1.0) / (r * 4.6)))) + (1 if int(round((w - 1.0) / (r * 4.6))) % 2 else 0)
    ns = max(3, int(round((d - 1.0) / (r * 4.6))))
    cols = []
    for i in range(nf):
        x = -w / 2 + 0.7 + (w - 1.4) * i / (nf - 1)
        cols += [(x, -d / 2 + 0.7), (x, d / 2 - 0.7)]
    for j in range(1, ns - 1):
        y = -d / 2 + 0.7 + (d - 1.4) * j / (ns - 1)
        cols += [(-w / 2 + 0.7, y), (w / 2 - 0.7, y)]
    for (x, y) in cols:
        a.stack([(pod, ring(10, r * 1.25, r * 1.25), x, y), (pod + 0.25, ring(10, r * 1.15, r * 1.15), x, y)], mm)
        a.stack([(pod + 0.25, ring(12, r, r, 0.05), x, y), (pod + colh - 0.5, ring(12, r * 0.86, r * 0.86, 0.05), x, y)], mm, False, False)
        a.box((x, y, pod + colh - 0.3), (r * 2.6, r * 2.6, 0.35), mm)
    ez = pod + colh
    a.box((0, 0, ez + 0.35), (w, d, 0.7), mm)
    a.box((0, 0, ez + 0.95), (w + 0.05, d + 0.05, 0.5), mc)
    a.box((0, 0, ez + 0.72), (w + 0.08, d + 0.08, 0.08), mg)
    a.box((0, 0, ez + 1.3), (w + 0.4, d + 0.4, 0.22), mm)
    gz = ez + 1.4
    gh = w * 0.2
    for sgn in (-1, 1):
        y = sgn * (d / 2 + 0.2)
        tri = [(-w / 2 - 0.2, y, gz), (w / 2 + 0.2, y, gz), (0, y, gz + gh)]
        a.poly(tri if sgn > 0 else tri[::-1], mm)
        inner = [(-w / 2 + 0.5, y - sgn * 0.08, gz + 0.2), (w / 2 - 0.5, y - sgn * 0.08, gz + 0.2), (0, y - sgn * 0.08, gz + gh - 0.3)]
        a.poly(inner if sgn > 0 else inner[::-1], mc)
    a.poly([(-w / 2 - 0.2, -d / 2 - 0.2, gz), (-w / 2 - 0.2, d / 2 + 0.2, gz), (0, d / 2 + 0.2, gz + gh), (0, -d / 2 - 0.2, gz + gh)], mr)
    a.poly([(w / 2 + 0.2, d / 2 + 0.2, gz), (w / 2 + 0.2, -d / 2 - 0.2, gz), (0, -d / 2 - 0.2, gz + gh), (0, d / 2 + 0.2, gz + gh)], mr)
    a.cone((0, -d / 2 - 0.2, gz + gh), 0.5, 1.6, mg, 4)
    for sx in (-1, 1):
        a.cone((sx * (w / 2), -d / 2 - 0.2, gz + 0.1), 0.35, 0.9, mg, 4)
        a.cone((sx * (w / 2), d / 2 + 0.2, gz + 0.1), 0.35, 0.9, mg, 4)
    if front_banners:
        for sx in (-1, 1):
            banner_flat(a, (sx * w * 0.32, -d / 2 - 0.1, ez - 0.4), w * 0.14, colh * 0.62, 0.0)


def banner_flat(a, top, width, length, yaw):
    x, y, z = top
    R = Matrix.Rotation(yaw, 3, "Z")
    hw, tail = width / 2, width * 0.45
    def p(u, v):
        return tuple(Vector((x, y, z)) + R @ Vector((u, -0.06, v)))
    a.poly([p(-hw, 0), p(hw, 0), p(hw, -(length - tail)), p(0, -length), p(-hw, -(length - tail))][::-1], a.key(CRIMSON))
    gk = a.key(GOLD, 0.5, 0.4)
    def q(u, v):
        return tuple(Vector((x, y, z)) + R @ Vector((u, -0.075, v)))
    cz = -length * 0.4
    rr = width * 0.3
    for sx in (-1, 1):
        for i in range(7):
            ang = -1.3 + i * 0.42
            lu, lv = sx * math.sin(ang + math.pi / 2) * rr, cz - math.cos(ang + math.pi / 2) * rr * 1.1
            dl = rr * 0.22
            a.poly([q(lu - dl * 0.6, lv), q(lu, lv + dl * 1.2), q(lu + dl * 0.6, lv), q(lu, lv - dl * 0.7)][::-1], gk)
    a.poly([q(-width * 0.38, -0.12), q(width * 0.38, -0.12), q(width * 0.38, -0.2), q(-width * 0.38, -0.2)][::-1], gk)
    a.box(p(0, 0.05), (width + 0.3, 0.12, 0.12), a.key(GOLD, 0.5, 0.4), yaw)


def tree(a, base, h, kind="cypress"):
    x, y, z = base
    if kind == "cypress":
        a.stack([(z, ring(6, h * 0.1, h * 0.1, 0.1), x, y), (z + h * 0.35, ring(6, h * 0.14, h * 0.14, 0.14), x, y), (z + h * 0.78, ring(6, h * 0.08, h * 0.08, 0.1), x, y),
                 (z + h, ring(6, 0.04, 0.04), x, y)], a.key(TREE))
    else:
        a.tube([(x, y, z), (x + 0.3, y, z + h * 0.7)], [0.2, 0.14], a.key("6b4a2e"), 5)
        a.stack([(z + h * 0.62, ring(8, h * 0.22, h * 0.22, 0.1), x + 0.3, y), (z + h * 0.82, ring(8, h * 0.4, h * 0.38, 0.12), x + 0.3, y),
                 (z + h * 0.95, ring(8, h * 0.25, h * 0.25, 0.1), x + 0.3, y)], a.key(PINE))


WALKERS = []      # (centre, radius, count, ground z) requests; real articulated citizens are spawned later


def people(a, center, radius, n, rng, z):
    WALKERS.append((tuple(center), radius, n, z))


def spawn_walkers(rng, frames, budget=150):
    total = sum(r[2] for r in WALKERS)
    k = min(1.0, budget / max(1, total))
    made = 0
    for (cx, cy), radius, n, z in WALKERS:
        for _ in range(max(1, int(round(n * k))) if n * k >= 0.5 else 0):
            fig = C.Figure("citizen", C.citizen_spec(rng))
            fig.build()
            root, piv = C.articulate(fig)
            pts = []
            for q in range(rng.randint(2, 4)):
                ang = rng.uniform(0, 2 * math.pi)
                r = radius * math.sqrt(rng.random())
                pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r, z))
            if rng.random() < 0.2:
                # a few stand and talk instead of walking
                root.location = pts[0]
                root.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
            else:
                C.animate_walk(root, piv, pts, rng.uniform(1.0, 1.5), 24, 1, frames, 0.55, rng.random())
            made += 1
    return made


def arch(a, x, y, z, yaw, w=14.0, h=13.0, d=4.0):
    at(a, x, y, z, yaw)
    mm, m2, mg = a.key(MARBLE), a.key(MARBLE2), a.key(GOLD, 0.5, 0.4)
    pw = w * 0.28
    for sx in (-1, 1):
        a.box((sx * (w / 2 - pw / 2), 0, h * 0.35), (pw, d, h * 0.7), mm)
        for k in (-1, 1):
            a.tube([(sx * (w / 2 - pw / 2) + k * pw * 0.35, -d / 2 - 0.35, 0.8), (sx * (w / 2 - pw / 2) + k * pw * 0.35, -d / 2 - 0.35, h * 0.68)], [0.32, 0.28], mm, 8)
    seg = 8
    ow = w - 2 * pw
    for k in range(seg):
        a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
        for s2 in (-1, 1):
            yy = s2 * d / 2
            pts = [(math.cos(a0) * ow / 2, yy, h * 0.52 + math.sin(a0) * ow / 2), (math.cos(a1) * ow / 2, yy, h * 0.52 + math.sin(a1) * ow / 2),
                   (math.cos(a1) * ow / 2 * 0 + math.cos(a1) * (ow / 2 + 0.1), yy, h * 0.72), (math.cos(a0) * (ow / 2 + 0.1), yy, h * 0.72)]
            a.poly(pts if s2 < 0 else pts[::-1], mm)
        a.poly([(math.cos(a1) * ow / 2, -d / 2, h * 0.52 + math.sin(a1) * ow / 2), (math.cos(a0) * ow / 2, -d / 2, h * 0.52 + math.sin(a0) * ow / 2),
                (math.cos(a0) * ow / 2, d / 2, h * 0.52 + math.sin(a0) * ow / 2), (math.cos(a1) * ow / 2, d / 2, h * 0.52 + math.sin(a1) * ow / 2)], m2)
    a.box((0, 0, h * 0.86), (w + 0.6, d + 0.6, h * 0.28), mm)
    a.box((0, -d / 2 - 0.32, h * 0.86), (w * 0.6, 0.05, h * 0.16), a.key(CRIMSON))
    a.box((0, 0, h * 0.72 + 0.05), (w + 0.7, d + 0.7, 0.25), mg)
    # a gilded quadriga-ish group on top
    a.box((0, 0, h + 0.6), (w * 0.35, d * 0.5, 1.2), mg)
    a.cone((0, 0, h + 1.2), 0.9, 2.2, mg, 4)
    a.T = Matrix.Identity(4)


def aqueduct(a, p0, p1, z, h):
    p0, p1 = Vector(p0), Vector(p1)
    n = int((p1 - p0).length / 9.0)
    d = (p1 - p0).normalized()
    yaw = math.atan2(d.y, d.x)
    for i in range(n + 1):
        p = p0.lerp(p1, i / n)
        a.box((p.x, p.y, z + h * 0.32), (1.8, 2.6, h * 0.64), a.key(MARBLE3), yaw)
        a.box((p.x, p.y, z + h * 0.8), (1.4, 2.2, h * 0.32), a.key(MARBLE3), yaw)
    mid = (p0 + p1) / 2
    ln = (p1 - p0).length
    a.box((mid.x, mid.y, z + h * 0.66), (ln, 2.8, 0.9), a.key(MARBLE2), yaw)
    a.box((mid.x, mid.y, z + h), (ln, 2.6, 1.0), a.key(MARBLE2), yaw)


def amphitheatre(a, x, y, z, r=46.0):
    n = 40
    mm, m2, dk = a.key(MARBLE2), a.key(MARBLE), a.key("4a3a3c")
    a.stack([(z, ring(n, r, r * 0.82), x, y), (z + 20, ring(n, r, r * 0.82), x, y)], mm, False, True)
    for row in range(3):
        for k in range(n):
            t = 2 * math.pi * (k + 0.5) / n
            px, py = x + math.cos(t) * r * 1.002, y + math.sin(t) * r * 0.82 * 1.002
            nx, ny = math.cos(t), math.sin(t) * 0.82
            tl = Vector((-ny, nx, 0)).normalized()
            zz = z + 1.5 + row * 6.0
            c = Vector((px, py, zz))
            a.poly([tuple(c - tl * 1.4), tuple(c + tl * 1.4), tuple(c + tl * 1.4 + Vector((0, 0, 3.6))), tuple(c - tl * 1.4 + Vector((0, 0, 3.6)))], dk)
        a.stack([(z + 5.2 + row * 6, ring(n, r * 1.01, r * 0.83), x, y), (z + 5.6 + row * 6, ring(n, r * 1.01, r * 0.83), x, y)], m2, False, False)
    a.stack([(z + 20.01, ring(n, r * 0.62, r * 0.48), x, y), (z + 20.02, ring(n, r * 0.62, r * 0.48), x, y)], a.key("c9b08a"))


# ----------------------------------------------------------------------------- the city plan
FORUM = (-6.0, -150.0, 80.0, 56.0)          # centre x, y, width, depth
ACRO = (-30.0, -420.0)                        # the capitol hill


def build_city(rng):
    accs = {}
    def acc_for(x, y):
        dist = (Vector((x, y, CITY_Z)) - CAM).length
        band = min(5, int(max(0.0, dist - 120) / 140))
        k = (band, int((x + 2000) // 300), int((y + 2000) // 300))
        if k not in accs:
            accs[k] = Acc("City_%d_%d_%d" % k)
            accs[k].haze = band * 0.06
        return accs[k], dist

    # ground: the plain, the paved city, the palace hill falling away below the balcony
    g, _ = acc_for(0, -300)
    g.T = Matrix.Identity(4)
    g.poly([(-3000, -3000, CITY_Z - 0.4), (3000, -3000, CITY_Z - 0.4), (3000, 3000, CITY_Z - 0.4), (-3000, 3000, CITY_Z - 0.4)], g.key("a88f6c"))
    g.poly([(-700, -900, CITY_Z), (700, -900, CITY_Z), (700, -20, CITY_Z), (-700, -20, CITY_Z)], g.key("cdb894"))
    blk, street = 34.0, 8.0
    for i in range(-20, 21):
        x = i * (blk + street)
        g.poly([(x - street / 2, -900, CITY_Z + 0.03), (x + street / 2, -900, CITY_Z + 0.03), (x + street / 2, -20, CITY_Z + 0.03), (x - street / 2, -20, CITY_Z + 0.03)], g.key("ddcdb0"))
    for j in range(1, 22):
        y = -20 - j * (blk + street)
        g.poly([(-700, y - street / 2, CITY_Z + 0.04), (700, y - street / 2, CITY_Z + 0.04), (700, y + street / 2, CITY_Z + 0.04), (-700, y + street / 2, CITY_Z + 0.04)], g.key("ddcdb0"))

    fx, fy, fw, fd = FORUM
    ax, ay = ACRO
    for i in range(-16, 17):
        for j in range(1, 22):
            cx = i * (blk + street) + (blk + street) / 2
            cy = -20 - j * (blk + street) + (blk + street) / 2
            if abs(cx - fx) < fw / 2 + 24 and abs(cy - fy) < fd / 2 + 26:
                continue
            if abs(cx - ax) < 120 and abs(cy - ay) < 110:
                continue
            if abs(cx - fx) < 14 and fy - fd / 2 > cy > ay + 110:
                continue      # the processional way from the forum to the capitol
            if (Vector((cx, cy)) - Vector((-250, -330))).length < 70:
                continue
            a, dist = acc_for(cx, cy)
            detail = dist < 420
            roll = rng.random()
            if roll < 0.1 and dist < 700:
                at(a, cx, cy, CITY_Z, rng.choice((math.pi, math.pi, math.pi / 2, -math.pi / 2)))
                temple(a, rng.uniform(13, 17), rng.uniform(20, 26), rng.uniform(8, 10), rng, True)
            elif roll < 0.11:
                at(a, cx, cy, CITY_Z, 0.0)
                a.box((0, 0, 0.15), (blk, blk, 0.3), a.key("6f8f45"))
                for _ in range(rng.randint(5, 10)):
                    tree(a, (rng.uniform(-14, 14), rng.uniform(-14, 14), 0.3), rng.uniform(7, 12), "cypress" if rng.random() < 0.6 else "pine")
            elif roll < 0.3 and detail:
                at(a, cx, cy, CITY_Z, 0.0)
                domus(a, blk * 0.9, rng, detail)
            else:
                # two to four insulae per block, of different heights
                splits = rng.choice(((1, 1), (2, 1), (1, 2), (2, 2)))
                for u in range(splits[0]):
                    for v in range(splits[1]):
                        bw = blk / splits[0] - 1.2
                        bd = blk / splits[1] - 1.2
                        bx = cx - blk / 2 + (u + 0.5) * blk / splits[0]
                        by = cy - blk / 2 + (v + 0.5) * blk / splits[1]
                        at(a, bx, by, CITY_Z, 0.0)
                        floors = rng.choice((2, 2, 3, 3, 3, 4)) if dist < 600 else rng.choice((2, 3))
                        insula(a, bw * rng.uniform(0.85, 1.0), bd * rng.uniform(0.85, 1.0), floors, rng, detail, dist < NEAR)
                at(a, cx, cy, CITY_Z, 0.0)
                for _ in range(rng.randint(0, 2)):
                    tree(a, (rng.choice((-1, 1)) * (blk / 2 + 1.5), rng.uniform(-blk / 2, blk / 2), 0.0), rng.uniform(7, 11), "cypress")
            if dist < 380 and rng.random() < 0.5:
                a.T = Matrix.Identity(4)
                people(a, (cx + blk / 2 + street / 2, cy), 3.0, rng.randint(1, 4), rng, CITY_Z)

    # the forum: paving, colonnades with banners, a statue fountain, the arch, the basilica
    a, _ = acc_for(fx, fy)
    a.T = Matrix.Identity(4)
    a.box((fx, fy, CITY_Z + 0.1), (fw, fd, 0.2), a.key("e6dcc8"))
    for k in range(int(fw / 6)):
        for l in range(int(fd / 6)):
            if (k + l) % 2 == 0:
                a.poly([(fx - fw / 2 + k * 6, fy - fd / 2 + l * 6, CITY_Z + 0.21), (fx - fw / 2 + k * 6 + 6, fy - fd / 2 + l * 6, CITY_Z + 0.21),
                        (fx - fw / 2 + k * 6 + 6, fy - fd / 2 + l * 6 + 6, CITY_Z + 0.21), (fx - fw / 2 + k * 6, fy - fd / 2 + l * 6 + 6, CITY_Z + 0.21)], a.key("d3c4a8"))
    for side in (-1, 1):
        x0 = fx + side * (fw / 2 + 3)
        a.box((x0 + side * 6, fy, CITY_Z + 6), (6, fd, 12), a.key("e9dcc4"))
        hip_roof_at(a, x0 + side * 4.5, fy, 10, fd + 2, CITY_Z + 12)
        for k in range(int(fd / 4.5) + 1):
            y = fy - fd / 2 + k * 4.5
            a.stack([(CITY_Z, ring(10, 0.55, 0.55), x0, y), (CITY_Z + 8.5, ring(10, 0.47, 0.47), x0, y)], a.key(MARBLE))
            a.box((x0, y, CITY_Z + 8.75), (1.4, 1.4, 0.5), a.key(MARBLE))
        a.box((x0, fy, CITY_Z + 9.4), (1.6, fd + 1.5, 0.9), a.key(MARBLE))
        a.box((x0, fy, CITY_Z + 10.0), (1.7, fd + 1.6, 0.35), a.key(CRIMSON))
        for k in range(5):
            y = fy - fd / 2 + 6 + k * (fd - 12) / 4
            banner_flat(a, (x0 - side * 0.9, y, CITY_Z + 9.0), 2.4, 6.0, -side * math.pi / 2)
    # fountain with a statue
    a.stack([(CITY_Z + 0.2, ring(8, 9, 9, 0, math.pi / 8), fx, fy), (CITY_Z + 1.3, ring(8, 9, 9, 0, math.pi / 8), fx, fy)], a.key(MARBLE))
    a.stack([(CITY_Z + 1.1, ring(8, 8.3, 8.3, 0, math.pi / 8), fx, fy), (CITY_Z + 1.15, ring(8, 8.3, 8.3, 0, math.pi / 8), fx, fy)], a.key("5aa3c4", 0.05))
    a.stack([(CITY_Z + 1.1, ring(8, 2.2, 2.2), fx, fy), (CITY_Z + 6.5, ring(8, 1.7, 1.7), fx, fy)], a.key(MARBLE2))
    people(a, (fx, fy - 18), 22, 70, rng, CITY_Z + 0.2)
    people(a, (fx, fy + 16), 18, 40, rng, CITY_Z + 0.2)
    arch(a, fx, fy - fd / 2 - 6, CITY_Z, 0.0)
    a.T = Matrix.Identity(4)
    # the processional way up to the capitol, lined with cypresses and banners
    for k in range(14):
        y = fy - fd / 2 - 8 - k * 14
        for sx in (-1, 1):
            tree(a, (fx + sx * 11, y, CITY_Z), 9.0, "cypress")

    # the capitol: three terraces, a grand stair, the great temple with its gilded spire
    a, _ = acc_for(ax, ay)
    a.T = Matrix.Identity(4)
    z = CITY_Z
    for (w, d, h) in ((230, 200, 14), (170, 150, 14), (120, 104, 12)):
        a.box((ax, ay, z + h / 2), (w, d, h), a.key("ddd0b8"))
        a.box((ax, ay, z + h - 0.3), (w + 1.2, d + 1.2, 0.6), a.key(MARBLE))
        arcade_wall(a, ax - w / 2, ax + w / 2, ay + d / 2 + 0.01, z, h, (ax - 19, ax + 19))
        for k in range(int(w / 9)):
            x = ax - w / 2 + 4.5 + k * 9
            a.box((x, ay + d / 2 + 0.4, z + h / 2), (1.2, 0.8, h), a.key(MARBLE2))
            if k % 3 == 1 and abs(x - ax) > 20:
                banner_flat(a, (x + 4.5, ay + d / 2 + 0.5, z + h - 0.8), 3.2, h * 0.7, math.pi)
        z += h
    z2 = CITY_Z
    for li, (w, d, h) in enumerate(((230, 200, 14), (170, 150, 14))):
        top = z2 + h
        nxt = ((170, 150), (120, 104))[li]
        for k in range(9):
            for side in (-1, 1):
                bx = ax + side * (nxt[0] / 2 + (w - nxt[0]) / 4)
                by = ay - d / 2 + 14 + k * (d - 28) / 8
                at(a, bx, by, top, 0.0)
                if k % 3 == 1:
                    a.T = a.T @ Matrix.Rotation(math.pi, 4, "Z")
                    temple(a, 12, 16, 7, rng, True)
                else:
                    insula(a, (w - nxt[0]) / 2 - 8, 12, 2, rng, True)
        for k in range(10):
            fxk = ax - nxt[0] / 2 + 6 + k * (nxt[0] - 12) / 9
            if abs(fxk - ax) > 22:
                at(a, fxk, ay + nxt[1] / 2 + (d - nxt[1]) / 4, top, 0.0)
                if k % 2:
                    insula(a, 10, (d - nxt[1]) / 2 - 6, 2, rng, True)
                else:
                    a.T = Matrix.Identity(4)
                    tree(a, (fxk, ay + nxt[1] / 2 + (d - nxt[1]) / 4, top), 10, "cypress")
        z2 = top
    steps = 40
    for i in range(steps):
        y = ay + 100 + 6 - i * (100 - 52) / steps * 1.0
        a.box((ax, y, CITY_Z + (i + 0.5) * (40.0 / steps) / 2), (34, (100 - 52) / steps + 0.3, (i + 1) * (40.0 / steps)), a.key(MARBLE))
    for sx in (-1, 1):
        for k in range(7):
            tree(a, (ax + sx * 50, ay + 60 - k * 18, CITY_Z + 12), 10, "cypress")
            tree(a, (ax + sx * 40, ay + 30 - k * 12, CITY_Z + 24), 9, "cypress")
    at(a, ax, ay - 8, z, math.pi)
    temple(a, 48, 64, 21, rng, True, False)
    a.T = Matrix.Identity(4)
    a.tube([(ax, ay - 8, z + 26), (ax, ay - 8, z + 54)], [2.6, 0.2], a.key(GOLD, 0.4, 0.5), 8)
    for sx in (-1, 1):
        at(a, ax + sx * 52, ay + 12, z - 12, math.pi)
        temple(a, 20, 28, 11, rng, True)
        at(a, ax + sx * 80, ay + 50, z - 26, math.pi)
        temple(a, 16, 22, 9, rng, True)
    people(a, (ax, ay + 75), 14, 40, rng, CITY_Z + 2.0)

    # the aqueduct striding in from the hills, and the amphitheatre
    a, _ = acc_for(-300, -420)
    a.T = Matrix.Identity(4)
    aqueduct(a, (-900, -620, 0), (-120, -280, 0), CITY_Z, 30)
    amphitheatre(a, -250, -330, CITY_Z)

    objs = [acc.build() for acc in accs.values()]
    return objs


def hip_roof_at(a, x, y, w, d, z):
    keep = a.T
    a.T = Matrix.Translation((x, y, 0)) @ keep
    hip_roof(a, w, d, z, a.key(ROOF), a.key("8a3a28"), 0.5, 0.3)
    a.T = keep


def build_horizon(rng):
    m = Acc("Mountains")
    for i in range(34):
        t = rng.uniform(-1.2, 1.2)
        dirv = Vector((math.sin(t), -math.cos(t), 0))
        r = rng.uniform(2600, 3400)
        c = dirv * r
        h = rng.uniform(90, 190)
        rx, ry = rng.uniform(450, 800), rng.uniform(250, 450)
        col = rgbhex([a + (b - a) * rng.uniform(0.0, 0.25) for a, b in zip(hexrgb("a291c0"), hexrgb("d1a8bd"))])
        pts = []
        for k in range(7):
            ang = 2 * math.pi * k / 7 + rng.uniform(-0.2, 0.2)
            pts.append((c.x + math.cos(ang) * rx * rng.uniform(0.8, 1.1), c.y + math.sin(ang) * ry * rng.uniform(0.8, 1.1), CITY_Z - 5))
        peak = (c.x + rng.uniform(-60, 60), c.y + rng.uniform(-60, 60), CITY_Z + h)
        mid = [((p[0] * 0.55 + peak[0] * 0.45) + rng.uniform(-30, 30), (p[1] * 0.55 + peak[1] * 0.45) + rng.uniform(-30, 30), CITY_Z + h * rng.uniform(0.4, 0.6)) for p in pts]
        k1 = m.key(col, 0.95)
        k2 = m.key(rgbhex([v * 1.08 for v in hexrgb(col)]), 0.95)
        for k in range(7):
            j = (k + 1) % 7
            m.poly([pts[k], pts[j], mid[j], mid[k]], k1)
            m.poly([mid[k], mid[j], peak], k2)
    objs = [m.build()]
    # faceted evening clouds and the setting sun
    cl = Acc("Clouds")
    # painterly key for the clouds: from above, the low sun and a little from the viewer's side
    tosun = (Vector((0, 0, 1)) * 0.8 + Vector((SUN_DIR.x, SUN_DIR.y, 0.0)) * 0.45 + Vector((0, 1, 0)) * 0.35).normalized()
    gold = [cl.key("ffd08a", 0.9, 0, "ffc070", 1.6), cl.key("f8b47a", 0.9, 0, "f4a268", 1.3), cl.key("eda08a", 0.9, 0, "e8907e", 1.0),
            cl.key("c793a8", 0.9, 0, "b886a2", 0.8), cl.key("a98ab8", 0.9, 0, "977cae", 0.7)]
    for i in range(8):
        t = rng.uniform(-0.75, 0.62)
        d = rng.uniform(1000, 1500)
        elev = math.radians(rng.uniform(6.5, 17))
        c = CAM + Vector((math.sin(t), -math.cos(t), 0)) * d + Vector((0, 0, d * math.tan(elev)))
        yaw = t + rng.uniform(-0.35, 0.35)
        tilt = rng.uniform(-0.12, 0.12)
        L = rng.uniform(220, 520)
        lumps = rng.randint(4, 8)
        for k in range(lumps):
            u = (k / max(1, lumps - 1) - 0.5) * L
            centre = c + Vector((math.cos(yaw), math.sin(yaw), tilt)) * u + Vector((0, 0, rng.uniform(-8, 12)))
            sx = rng.uniform(90, 170) * (1.0 - abs(u) / L * 0.8)
            sz = rng.uniform(12, 26) * (1.0 - abs(u) / L * 0.7)
            sy = sx * 0.45
            segs, rings = 7, 4
            grid = []
            for r in range(rings + 1):
                ph = math.pi * r / rings
                row = []
                for q in range(segs):
                    th = 2 * math.pi * q / segs + (0.4 if r % 2 else 0.0)
                    z = math.cos(ph)
                    z = max(z, -0.35)          # flattened underside
                    v = Vector((math.sin(ph) * math.cos(th) * sx, math.sin(ph) * math.sin(th) * sy, z * sz))
                    v.rotate(Euler((0, 0, yaw)))
                    row.append(centre + v)
                grid.append(row)
            for r in range(rings):
                for q in range(segs):
                    qa, qb = q, (q + 1) % segs
                    for tri in ((grid[r][qa], grid[r + 1][qa], grid[r + 1][qb]), (grid[r][qa], grid[r + 1][qb], grid[r][qb])):
                        n = (tri[1] - tri[0]).cross(tri[2] - tri[0])
                        if n.length < 1e-6:
                            continue
                        n.normalize()
                        if n.dot(centre - (tri[0] + tri[1] + tri[2]) / 3) > 0:
                            n = -n
                        lit = n.dot(tosun)
                        idx = 0 if lit > 0.55 else 1 if lit > 0.2 else 2 if lit > -0.15 else 3 if lit > -0.5 else 4
                        cl.poly([tuple(p) for p in tri], gold[idx])
    objs.append(cl.build())
    sun = Acc("SunDisc")
    sc = CAM + SUN_DIR * 2600
    k = sun.key("ffe6a8", 0.5, 0, "ffd070", 25.0)
    u = SUN_DIR.cross(Vector((0, 0, 1))).normalized()
    v = u.cross(SUN_DIR).normalized()
    pts = [tuple(sc + (u * math.cos(2 * math.pi * q / 16) + v * math.sin(2 * math.pi * q / 16)) * 28) for q in range(16)]
    sun.poly(pts, k)
    halo = sun.key("ffb060", 0.5, 0, "ffa050", 3.0)
    pts2 = [tuple(sc - SUN_DIR * 5 + (u * math.cos(2 * math.pi * q / 16) + v * math.sin(2 * math.pi * q / 16)) * 75) for q in range(16)]
    sun.poly(pts2, halo)
    objs.append(sun.build())
    for o in objs:
        o.visible_shadow = False
    return objs


# ----------------------------------------------------------------------------- the balcony
def build_balcony(rng):
    a = Acc("Balcony")
    # marble floor (checker of large slabs), stepping down to the balustrade
    for i in range(-8, 7):
        for j in range(-1, 6):
            x0, y0 = i * 2.0, j * 2.0
            k = a.key("e6dcd6" if (i + j) % 2 == 0 else "d2c4bc", 0.75)
            a.poly([(x0, y0, 0), (x0 + 2, y0, 0), (x0 + 2, y0 + 2, 0), (x0, y0 + 2, 0)], k)
    # the carpet: crimson with a gold border, from the doors to the balustrade
    a.box((-2.6, 5.0, 0.01), (3.6, 12.0, 0.02), a.key("c8862d", 0.6))
    a.box((-2.6, 5.0, 0.025), (3.0, 12.2, 0.02), a.key(CRIMSON, 0.9))
    # the balustrade with turned balusters and plinth posts
    def balustrade(p0, p1):
        p0, p1 = Vector(p0), Vector(p1)
        L = (p1 - p0).length
        d = (p1 - p0).normalized()
        yaw = math.atan2(d.y, d.x)
        mid = (p0 + p1) / 2
        a.box((mid.x, mid.y, 0.11), (L + 0.5, 0.6, 0.22), a.key(MARBLE2), yaw)
        a.box((mid.x, mid.y, 0.8), (L + 0.5, 0.62, 0.15), a.key(MARBLE), yaw)
        a.box((mid.x, mid.y, 0.71), (L + 0.4, 0.5, 0.05), a.key(GOLD, 0.5, 0.4), yaw)
        n = int(L / 0.34)
        for k in range(n):
            p = p0 + d * (L * (k + 0.5) / n)
            if k % 10 == 5:
                a.box((p.x, p.y, 0.45), (0.55, 0.55, 0.72), a.key(MARBLE), yaw)
                continue
            a.stack([(0.22, ring(8, 0.07, 0.07), p.x, p.y), (0.35, ring(8, 0.125, 0.125), p.x, p.y), (0.45, ring(8, 0.085, 0.085), p.x, p.y),
                     (0.58, ring(8, 0.065, 0.065), p.x, p.y), (0.68, ring(8, 0.095, 0.095), p.x, p.y), (0.73, ring(8, 0.08, 0.08), p.x, p.y)], a.key("d9cdb6", 0.6))
    balustrade((-16, -2.0), (14, -2.0))
    balustrade((14, -2.0), (14, 8.0))
    # the balcony's edge: a cornice and the retaining wall falling to the city
    a.box((-1, -2.6, -0.4), (32, 1.4, 0.8), a.key(MARBLE))
    a.box((-1, -3.4, CITY_Z / 2), (36, 2.0, -CITY_Z), a.key("d8c7a8"))
    for k in range(10):
        x = -16 + k * 3.6
        a.box((x, -4.2, CITY_Z / 2), (1.4, 1.2, -CITY_Z), a.key("cdb99a"))
    # the colonnade on the left, belonging to the palace wing
    for y in (-1.6, 1.0, 3.6):
        x = -4.6
        a.box((x, y, 0.2), (1.6, 1.6, 0.4), a.key(MARBLE2))
        a.stack([(0.4, ring(16, 0.62, 0.62, 0.04), x, y), (6.8, ring(16, 0.55, 0.55, 0.04), x, y)], a.key(MARBLE), False, False)
        a.stack([(6.8, ring(12, 0.6, 0.6), x, y), (7.1, ring(12, 0.74, 0.74), x, y)], a.key(GOLD, 0.5, 0.4))
        a.box((x, y, 7.3), (1.9, 1.3, 0.4), a.key(MARBLE))
        for sy in (-1, 1):
            a.tube([(x - 0.75, y + sy * 0.55, 7.25), (x + 0.75, y + sy * 0.55, 7.25)], [0.24, 0.24], a.key(MARBLE), 8)
        a.box((x, y, 7.65), (2.0, 2.0, 0.3), a.key(MARBLE))
    a.box((-4.6, 1.0, 8.3), (2.4, 12.0, 1.0), a.key(MARBLE))
    a.box((-4.6, 1.0, 8.95), (2.5, 12.1, 0.3), a.key(CRIMSON))
    a.box((-4.6, 1.0, 9.3), (2.9, 12.4, 0.4), a.key(MARBLE))
    a.box((-10.1, 4.0, 6.0), (6.0, 16.0, 12.0), a.key("e3d2b6"))
    for (x, y) in ((-5.3, 1.5), (-5.3, 5.7)):
        a.box((x, y, 2.3), (0.2, 2.2, 4.4), a.key("3e2c30"))
    # banners hung between the columns, and on a tall pole by the brazier
    banner_flat(a, (-3.6, -0.4, 6.4), 0.85, 3.3, math.pi)
    a.box((-3.6, -0.4, 6.5), (1.2, 0.08, 0.08), a.key(GOLD, 0.5, 0.4))
    a.tube([(-3.6, -0.4, 6.5), (-4.6, -0.9, 7.0)], [0.04, 0.04], a.key(GOLD, 0.5, 0.4), 4)
    banner_flat(a, (-4.15, 1.0, 6.9), 0.8, 3.0, math.pi * 0.5)
    px, py = 5.2, -0.6
    a.tube([(px, py, 0), (px, py, 6.4)], [0.08, 0.07], a.key(GOLD, 0.45, 0.5), 6)
    a.box((px - 0.8, py, 6.1), (2.2, 0.12, 0.12), a.key(GOLD, 0.45, 0.5))
    banner_flat(a, (px - 0.6, py + 0.1, 6.0), 0.95, 3.5, math.pi)
    # the statue's pedestal at the balustrade
    a.box((-2.25, -1.3, 0.55), (1.3, 1.3, 1.1), a.key(MARBLE2))
    a.box((-2.25, -1.3, 1.15), (1.5, 1.5, 0.12), a.key(MARBLE))
    o = a.build()
    parts = [o]
    # the brazier with real faceted fire, and the statue with a spear

    spec = dict(C.CAST["thane"], headwear="none", prop="spear", cloak="x")
    parts += statue_on(spec, -2.25, -1.3, 1.21, 0.35, 1.4)
    return parts


def fire_bowl(x, y, s=1.5):
    a = Acc("FireBowl")
    a.stack([(0, ring(8, 0.45 * s, 0.45 * s), x, y), (0.2 * s, ring(8, 0.42 * s, 0.42 * s), x, y), (0.75 * s, ring(8, 0.22 * s, 0.22 * s), x, y)], a.key("8a5a2a", 0.4, 0.6))
    a.stack([(0.7 * s, ring(10, 0.22 * s, 0.22 * s), x, y), (0.82 * s, ring(10, 0.5 * s, 0.5 * s), x, y), (1.05 * s, ring(10, 0.68 * s, 0.68 * s), x, y),
             (1.22 * s, ring(10, 0.74 * s, 0.74 * s), x, y), (1.27 * s, ring(10, 0.8 * s, 0.8 * s), x, y)], a.key("9a6428", 0.4, 0.6), True, False)
    a.stack([(1.18 * s, ring(10, 0.72 * s, 0.72 * s), x, y), (1.19 * s, ring(10, 0.72 * s, 0.72 * s), x, y)], a.key("3a1a10"))
    rr = random.Random(9)
    for i in range(8):
        ang = 2 * math.pi * i / 8 + rr.uniform(-0.2, 0.2)
        r = rr.uniform(0.1, 0.42) * s
        bx, by = x + math.cos(ang) * r, y + math.sin(ang) * r
        h = rr.uniform(0.6, 1.25) * s
        col = a.key(rr.choice(("ff7a18", "ff8a20", "f06010")), 0.5, 0, rr.choice(("ff4a00", "ff5a08", "e84000")), rr.uniform(1.4, 2.2))
        base = [(bx + math.cos(ang + k * 2.1) * 0.17 * s, by + math.sin(ang + k * 2.1) * 0.17 * s, 1.18 * s) for k in range(3)]
        tip = (bx + math.cos(ang) * 0.32 * s + rr.uniform(-0.1, 0.1), by + math.sin(ang) * 0.32 * s, 1.18 * s + h)
        for k in range(3):
            a.poly([base[k], base[(k + 1) % 3], tip], col)
    core = a.key("ffb030", 0.5, 0, "ff9a10", 2.6)
    base = [(x + math.cos(k * 2.1) * 0.35 * s, y + math.sin(k * 2.1) * 0.35 * s, 1.18 * s) for k in range(3)]
    for k in range(3):
        a.poly([base[k], base[(k + 1) % 3], (x, y, 1.18 * s + 0.95 * s)], core)
    a.build()
    bpy.ops.object.light_add(type="POINT", location=(x, y, 2.4 * s))
    l = bpy.context.active_object
    l.data.energy = 900
    l.data.color = (1.0, 0.6, 0.28)


def statue_on(spec, x, y, z, yaw, scale=1.6):
    marble = dict(spec)
    for k in ("skin", "hair", "primary", "secondary", "trim", "cloak", "shield", "lining"):
        if marble.get(k):
            marble[k] = "cdb48c"
    fig = C.Figure("statue", marble).build()
    for o in fig:
        o.data.materials.clear()
        o.data.materials.append(C.m("cdb48c", 0.7))
        for p in o.data.polygons:
            p.material_index = 0
    P.place(fig, (x, y, z), yaw, scale)
    return fig


def court():
    """The Emperor at the balustrade with his court behind him."""
    who = [("emperor", (-0.6, 3.7), 0.55, 1.38), ("herald", (-2.6, 1.6), 0.45, 1.0), ("treasurer", (-3.0, 0.4), 0.3, 1.0),
           ("aldric", (-3.4, 1.0), 0.6, 1.0), ("empress", (-3.6, 2.4), 0.2, 1.0), ("chancellor", (-2.9, -0.4), 0.4, 1.0), ("halvana", (-3.8, -0.2), 0.5, 1.0)]
    for cid, (x, y), yaw, sc in who:
        spec = C.CAST[cid]
        if cid == "emperor":
            spec = dict(spec, hair="4a2e1e", beard="full", prop="none")
        P.place(C.Figure(cid, spec).build(), (x, y, 0.03), yaw, sc)


def lighting(samples):
    P.lighting(samples)
    sc = bpy.context.scene
    sun = [o for o in sc.objects if o.type == "LIGHT" and o.data.type == "SUN"][0]
    # key: the visible evening sun ahead, throwing long baluster shadows toward the viewer
    sun.rotation_euler = Vector((SUN_DIR.x, SUN_DIR.y, 0.32)).normalized().to_track_quat("Z", "Y").to_euler()
    sun.data.energy = 1.9
    sun.data.angle = math.radians(14.0)
    # a warm fill from behind the viewer, as in the painting: faces toward us read golden, not grey
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
    fill = bpy.context.active_object
    fill.data.energy = 1.35
    fill.data.color = (1.0, 0.74, 0.5)
    fill.data.use_shadow = False
    fill.rotation_euler = Vector((-0.45, 1.0, 0.6)).normalized().to_track_quat("Z", "Y").to_euler()
    sun.data.color = (1.0, 0.8, 0.6)
    w = sc.world.node_tree
    ramp = [n for n in w.nodes if n.type == "VALTORGB"][0].color_ramp
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[1])
    ramp.elements[0].position = 0.0
    ramp.elements[0].color = K.hexc("ffb35a")
    ramp.elements[1].position = 0.5
    ramp.elements[1].color = K.hexc("3e3487")
    for pos, col in ((0.05, "ffa06a"), (0.12, "e7849a"), (0.25, "8e6ec2")):
        ramp.elements.new(pos).color = K.hexc(col)
    w.nodes["Background"].inputs["Strength"].default_value = 0.85
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "Medium Contrast"
    except TypeError:
        sc.view_settings.look = "None"
    sc.cycles.max_bounces = 4
    sc.render.film_transparent = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--only", default="")
    ap.add_argument("--res", default="1672x941")
    ap.add_argument("--frames", type=int, default=72)
    ap.add_argument("--anim", action="store_true", help="render the street-level walking clip")
    args = ap.parse_args()
    rng = random.Random(4)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = build_city(rng) + build_horizon(rng)
    before = set(bpy.context.scene.objects)
    build_balcony(rng)
    court()
    nwalk = spawn_walkers(rng, args.frames)
    print("walkers:", nwalk)
    # the balcony is authored with the colonnade at -X; mirror it so the colonnade reads on the left
    mirror = bpy.data.objects.new("BalconyMirror", None)
    bpy.context.collection.objects.link(mirror)
    for o in set(bpy.context.scene.objects) - before:
        if o.parent is None and o is not mirror:
            o.parent = mirror
    mirror.scale = (-1, 1, 1)
    fire_bowl(-2.6, 2.2, 0.95)
    fx, fy, fw, fd = FORUM
    statue_on(dict(C.CAST["emperor"], prop="spear", cloak="x"), fx, fy, CITY_Z + 6.5, 0.0, 4.2)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.context.scene.objects if o.type == "MESH")
    print("scene triangles:", tris)
    lighting(args.samples)
    rx, ry = (int(v) for v in args.res.split("x"))
    out = os.path.join(ROOT, "renders")
    shots = {
        "balcony_hero": (tuple(CAM), (-6.0, -300.0, 3.0 - 307.5 * math.tan(math.radians(4.5))), 30),
        "balcony_city": ((6.0, -1.0, 2.4), (-10.0, -165.0, -34.0), 32),
    }
    for k, (loc, tgt, lens) in shots.items():
        if args.only and k not in args.only.split(","):
            continue
        bpy.context.scene.frame_set(1)
        K.shoot(os.path.join(out, k + ".png"), loc, tgt, lens, (rx, ry))
    if args.anim:
        fx, fy, fw, fd = FORUM
        sc = bpy.context.scene
        sc.frame_start, sc.frame_end = 1, args.frames
        sc.render.fps = 24
        sc.render.resolution_x, sc.render.resolution_y = 854, 480
        sc.cycles.samples = 8
        if sc.camera is None:
            bpy.ops.object.camera_add()
            sc.camera = bpy.context.active_object
        cam = sc.camera
        cam.data.clip_end = 8000.0
        cam.location = (fx + 10, fy + 30, CITY_Z + 1.7)
        cam.rotation_euler = (Vector((fx - 4, fy - 40, CITY_Z + 7)) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 28
        frames_dir = os.path.join(out, "walk_frames")
        os.makedirs(frames_dir, exist_ok=True)
        sc.render.filepath = os.path.join(frames_dir, "f_")
        sc.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(animation=True)
        print("animation frames", frames_dir)


if __name__ == "__main__":
    main()
