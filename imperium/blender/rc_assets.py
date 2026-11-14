"""Stage 4: the reusable architectural asset library.

Each asset is modelled once (hand-placed low-poly, flat colours) into the "Asset Library" collection,
hidden from render; the city places linked duplicates of these meshes. Categories:
  small (8), medium (8), large (5) residential; temple (4); tower (4); public (5); arch (4);
  monument (3); tree (4: three cypress and an umbrella pine);
  mid (8) and far (6) simplified buildings for the middle and far distance; skyline (3) far landmarks.
Assets face +Y (toward the camera) when unrotated; their origin is the ground centre.
"""
import math
import random

import bpy
from mathutils import Matrix, Vector

import rc_common as R
import city as T
from city import Acc, ring, hip_roof, temple, tree, banner_flat, facade_grand

MARBLE, MARBLE2, CRIMSON, GOLD = T.MARBLE, T.MARBLE2, T.CRIMSON, T.GOLD
WALLS = ["efe3cc", "e8d5b5", "f2e6d2", "e2c7a2", "eddabe", "e6cdb0", "f0dcc2", "dcb892", "e8c9a6", "d9b896", "efd7bc", "e4c3a0"]
ROOFS = ["b04e36", "9a4230", "a84a32", "be5c40", "9e4632", "b45a3c"]
LIB = {}


def _new(cat, name, a, dims):
    o = a.build()
    o.name = "ASSET_%s_%s" % (cat, name)
    o.hide_render = True
    o.hide_set(True)
    R.move_to(o, "Asset Library")
    LIB.setdefault(cat, []).append({"obj": o, "mesh": o.data, "dims": dims, "name": name})
    return o


# ----------------------------------------------------------------------------- roofs
def roof(a, kind, w, d, z, rng, col):
    rk, rd = a.key(col), a.key("8a3a28")
    if kind == "hip":
        hip_roof(a, w, d, z, rk, rd, 0.5, rng.uniform(0.15, 0.2))
    elif kind in ("gable_x", "gable_y"):
        along_x = kind == "gable_x"
        L, S = (w, d) if along_x else (d, w)
        h = S * rng.uniform(0.16, 0.21)
        o = 0.45
        def P(u, v, zz):
            return (u, v, zz) if along_x else (v, u, zz)
        a.poly([P(-L / 2 - o, -S / 2 - o, z), P(L / 2 + o, -S / 2 - o, z), P(L / 2 + o, 0, z + h), P(-L / 2 - o, 0, z + h)], rk)
        a.poly([P(L / 2 + o, S / 2 + o, z), P(-L / 2 - o, S / 2 + o, z), P(-L / 2 - o, 0, z + h), P(L / 2 + o, 0, z + h)], rk)
        for sgn in (-1, 1):
            a.poly([P(sgn * L / 2, -S / 2, z), P(sgn * L / 2, S / 2, z), P(sgn * L / 2, 0, z + h)][::sgn], a.key(MARBLE2))
        a.tube([P(-L / 2 - o, 0, z + h), P(L / 2 + o, 0, z + h)], [0.14, 0.14], rd, 4)
    elif kind == "flat":
        a.box((0, 0, z + 0.05), (w, d, 0.1), a.key("d6c4a6"))
        for k in range(int((w + d) * 2 / 0.9)):
            t = k * 0.9
            if t < w:
                p = (-w / 2 + t, d / 2)
            elif t < w + d:
                p = (w / 2, d / 2 - (t - w))
            elif t < 2 * w + d:
                p = (w / 2 - (t - w - d), -d / 2)
            else:
                p = (-w / 2, -d / 2 + (t - 2 * w - d))
            a.box((p[0], p[1], z + 0.45), (0.2, 0.2, 0.75), a.key(MARBLE))
        if rng.random() < 0.6:
            tree(a, (rng.uniform(-w / 4, w / 4), rng.uniform(-d / 4, d / 4), z + 0.1), rng.uniform(2.5, 4), rng.choice(("cypress", "pine")))
        if rng.random() < 0.5:
            # a pergola / awning
            for q in range(4):
                a.tube([(-w / 4 + (q % 2) * w / 2, -d / 4 + (q // 2) * d / 2, z), (-w / 4 + (q % 2) * w / 2, -d / 4 + (q // 2) * d / 2, z + 2.3)], [0.07, 0.07], a.key("6b4a2e"), 4)
            a.box((0, 0, z + 2.35), (w / 2 + 0.6, d / 2 + 0.6, 0.1), a.key(rng.choice(("c8862d", "8e1f24", "6b4a2e"))))
    elif kind == "lean":
        a.poly([(-w / 2 - 0.4, -d / 2 - 0.4, z), (w / 2 + 0.4, -d / 2 - 0.4, z), (w / 2 + 0.4, d / 2 + 0.4, z + d * 0.14), (-w / 2 - 0.4, d / 2 + 0.4, z + d * 0.14)], rk)
        a.box((0, d / 2, z + d * 0.07), (w, 0.3, d * 0.14), a.key(MARBLE2))


def house(a, w, d, floors, rng, roof_kind, wall=None, style=None, all_sides=True):
    """A residential block with framed facades on every side (one decorated front, toward +Y)."""
    wall = wall or rng.choice(WALLS)
    mats = {"wall": a.key(wall), "trim": a.key(MARBLE), "dark": a.key("5e4038", 0.9), "door": a.key("6a4430"), "shade": a.key("8a6a5e"),
            "frieze": a.key(CRIMSON), "roof": a.key(rng.choice(ROOFS)), "ridge": a.key("8a3a28"), "plinth": a.key(MARBLE2)}
    hf = rng.uniform(3.0, 3.5)
    H = floors * hf + 0.5
    a.box((0, 0, H / 2), (w, d, H), mats["wall"])
    a.box((0, 0, 0.35), (w + 0.12, d + 0.12, 0.7), mats["plinth"])
    for f in range(1, floors):
        a.box((0, 0, f * hf + 0.05), (w + 0.14, d + 0.14, 0.16), mats["trim"])
    a.box((0, 0, H - 0.1), (w + 0.4, d + 0.4, 0.3), mats["trim"])
    st = style or {"arcade": rng.random() < 0.5}
    for side in ((0, 1, 2, 3) if all_sides else (2, 1, 3)):
        facade_grand(a, w, d, hf, floors, side, mats, rng, st if side == 2 else {"arcade": st.get("arcade")})
    if floors >= 2 and rng.random() < 0.45:
        bw = min(w * 0.55, 4.5)
        side = rng.choice((1, 2, 3))
        a.T = a.T @ Matrix.Rotation({1: -math.pi / 2, 2: 0.0, 3: math.pi / 2}[side], 4, "Z")
        dd = d if side == 2 else w
        a.box((0, dd / 2 + 0.45, hf + 0.1), (bw, 0.9, 0.12), a.key("6b4a2e"))
        for k in range(int(bw / 0.45) + 1):
            a.box((-bw / 2 + k * 0.45, dd / 2 + 0.88, hf + 0.55), (0.06, 0.06, 0.9), a.key("6b4a2e"))
        a.box((0, dd / 2 + 0.88, hf + 1.0), (bw, 0.08, 0.08), a.key("6b4a2e"))
        a.T = a.T @ Matrix.Rotation(-{1: -math.pi / 2, 2: 0.0, 3: math.pi / 2}[side], 4, "Z")
    roof(a, roof_kind, w, d, H, rng, rng.choice(ROOFS))
    return H


# ----------------------------------------------------------------------------- categories
def build_residential(rng):
    kinds = ["hip", "gable_x", "gable_y", "flat", "hip", "lean", "gable_x", "flat"]
    for i in range(8):
        a = Acc("small%d" % i)
        w, d = rng.uniform(6, 10), rng.uniform(6, 10)
        fl = 1 + (i % 3 != 0)
        house(a, w, d, fl, rng, kinds[i])
        if i % 4 == 1:
            a.box((w / 2 + 1.6, 0, 1.4), (3.0, d * 0.7, 2.8), a.key(rng.choice(WALLS)))
            keep = a.T
            a.T = a.T @ Matrix.Translation((w / 2 + 1.6, 0, 0))
            T.hip_roof(a, 3.0, d * 0.7, 2.8, a.key(rng.choice(ROOFS)), a.key("8a3a28"), 0.3, 0.18)
            a.T = keep
        _new("small", str(i), a, (w + 2, d + 2))
    for i in range(8):
        a = Acc("medium%d" % i)
        w, d = rng.uniform(10, 16), rng.uniform(10, 16)
        fl = rng.choice((2, 3, 3, 3, 4))
        style = {"arcade": rng.random() < 0.7, "loggia": rng.random() < 0.5, "portico": i in (2, 6), "banner": i in (1, 5)}
        house(a, w, d, fl, rng, ["hip", "gable_x", "flat", "hip", "gable_y", "flat", "hip", "gable_x"][i], style=style)
        if i % 3 == 0:
            # a lower wing of a different height overlapping the block
            keep = a.T
            a.T = a.T @ Matrix.Translation((w * 0.45, -d * 0.2, 0))
            house(a, w * 0.5, d * 0.6, max(1, fl - 2), rng, "hip")
            a.T = keep
        _new("medium", str(i), a, (w + 3, d + 3))
    for i in range(5):
        a = Acc("large%d" % i)
        if i in (0, 3):
            # a courtyard block: four multi-storey wings around a garden
            s = rng.uniform(26, 34)
            t = s * 0.28
            fl = rng.choice((3, 4, 5))
            for (cx, cy, w, d) in ((0, -s / 2 + t / 2, s, t), (0, s / 2 - t / 2, s, t), (-s / 2 + t / 2, 0, t, s - 2 * t), (s / 2 - t / 2, 0, t, s - 2 * t)):
                keep = a.T
                a.T = a.T @ Matrix.Translation((cx, cy, 0))
                house(a, w, d, fl, rng, "hip" if w > d else "gable_y", style={"arcade": True, "loggia": cy > 0 and i == 0})
                a.T = keep
            a.box((0, 0, 0.15), (s - 2 * t, s - 2 * t, 0.3), a.key("6f8f45"))
            tree(a, (2, 1, 0.3), 7, "cypress")
            tree(a, (-3, -2, 0.3), 8, "pine")
            _new("large", str(i), a, (s + 2, s + 2))
        elif i in (1, 4):
            # stepped palace: a tall core with lower wings
            w, d = rng.uniform(22, 30), rng.uniform(16, 22)
            house(a, w, d, rng.choice((4, 5)), rng, "hip", style={"arcade": True, "loggia": True, "banner": True})
            for sx in (-1, 1):
                keep = a.T
                a.T = a.T @ Matrix.Translation((sx * (w / 2 + 5), 2, 0))
                house(a, 10, d * 0.8, 2, rng, "flat")
                a.T = keep
            _new("large", str(i), a, (w + 22, d + 4))
        else:
            # an L-shaped block
            w, d = rng.uniform(24, 30), rng.uniform(10, 13)
            house(a, w, d, 4, rng, "gable_x", style={"arcade": True, "portico": True})
            keep = a.T
            a.T = a.T @ Matrix.Translation((w / 2 - d / 2, -d / 2 - 7, 0))
            house(a, d, 14, 3, rng, "gable_y")
            a.T = keep
            _new("large", str(i), a, (w + 2, d + 18))


def tholos(a, r, colh):
    mm = a.key(MARBLE)
    a.stack([(0, ring(16, r + 2.0, r + 2.0), 0, 0), (1.6, ring(16, r + 2.0, r + 2.0), 0, 0)], a.key(MARBLE2))
    for k in range(16):
        ang = 2 * math.pi * k / 16
        a.stack([(1.6, ring(10, 0.45, 0.45, 0.04), math.cos(ang) * r, math.sin(ang) * r), (1.6 + colh, ring(10, 0.38, 0.38, 0.04), math.cos(ang) * r, math.sin(ang) * r)], mm, False, False)
    a.stack([(1.4, ring(16, r * 0.7, r * 0.7), 0, 0), (1.6 + colh, ring(16, r * 0.7, r * 0.7), 0, 0)], a.key("efe3cf"), False, False)
    a.stack([(1.6 + colh, ring(16, r + 0.6, r + 0.6), 0, 0), (2.6 + colh, ring(16, r + 0.6, r + 0.6), 0, 0)], mm)
    a.stack([(2.6 + colh, ring(16, r + 0.7, r + 0.7), 0, 0), (2.6 + colh + r * 0.45, ring(16, r * 0.35, r * 0.35), 0, 0), (2.8 + colh + r * 0.55, ring(16, 0.3, 0.3), 0, 0)], a.key(T.ROOF), False, True)


def build_temples(rng):
    specs = [(10, 14, 6.5), (16, 24, 9.0), (26, 38, 13.0)]
    for i, (w, d, ch) in enumerate(specs):
        a = Acc("temple%d" % i)
        a.T = Matrix.Rotation(math.pi, 4, "Z")
        temple(a, w, d, ch, rng, i > 0)
        _new("temple", str(i), a, (w + 4, d + 8))
    a = Acc("temple3")
    tholos(a, 7, 8)
    _new("temple", "3", a, (20, 20))


def build_towers(rng):
    for i in range(4):
        a = Acc("tower%d" % i)
        s = rng.uniform(6, 9)
        h = rng.uniform(22, 36)
        wall = rng.choice(WALLS)
        if i == 1:
            a.stack([(0, ring(12, s / 2, s / 2), 0, 0), (h, ring(12, s / 2 * 0.92, s / 2 * 0.92), 0, 0)], a.key(wall), True, False)
            a.stack([(h, ring(12, s / 2 + 0.4, s / 2 + 0.4), 0, 0), (h + 0.5, ring(12, s / 2 + 0.4, s / 2 + 0.4), 0, 0)], a.key(MARBLE))
            a.cone((0, 0, h + 0.5), s / 2 + 0.5, s * 0.5, a.key(rng.choice(ROOFS)), 12)
            for f in range(int(h / 4)):
                for k in range(4):
                    ang = 2 * math.pi * k / 4 + f * 0.4
                    a.box((math.cos(ang) * s / 2 * 0.93, math.sin(ang) * s / 2 * 0.93, 2.5 + f * 4), (0.9, 0.9, 1.4), a.key("5e4038"), ang)
        else:
            a.box((0, 0, h / 2), (s, s, h), a.key(wall))
            for f in range(int(h / 4)):
                for side in range(4):
                    ang = side * math.pi / 2
                    a.box((math.sin(ang) * (s / 2 + 0.02), -math.cos(ang) * (s / 2 + 0.02), 2.5 + f * 4), (1.0, 0.05, 1.5), a.key("5e4038"), ang)
                a.box((0, 0, 4.0 * f + 0.05), (s + 0.15, s + 0.15, 0.15), a.key(MARBLE))
            if i == 2:
                # an open loggia at the top under a tiled cap
                a.box((0, 0, h + 0.1), (s + 0.6, s + 0.6, 0.2), a.key(MARBLE))
                for q in range(4):
                    a.tube([((q % 2 - 0.5) * s, (q // 2 - 0.5) * s, h), ((q % 2 - 0.5) * s, (q // 2 - 0.5) * s, h + 3.6)], [0.35, 0.3], a.key(MARBLE), 8)
                a.box((0, 0, h + 3.8), (s + 0.8, s + 0.8, 0.4), a.key(MARBLE))
                hip_roof(a, s + 0.4, s + 0.4, h + 4.0, a.key(rng.choice(ROOFS)), a.key("8a3a28"), 0.4, 0.35)
                h += 4
            elif i == 3:
                # battlements
                a.box((0, 0, h + 0.3), (s + 1.0, s + 1.0, 0.6), a.key(MARBLE2))
                for k in range(16):
                    side = k // 4
                    u = -s / 2 + (k % 4 + 0.5) * s / 4
                    p = [(u, s / 2 + 0.3), (s / 2 + 0.3, -u), (-u, -s / 2 - 0.3), (-s / 2 - 0.3, u)][side]
                    a.box((p[0], p[1], h + 1.0), (0.7, 0.7, 0.9), a.key(MARBLE2))
            else:
                a.box((0, 0, h - 0.1), (s + 0.8, s + 0.8, 0.4), a.key(MARBLE))
                hip_roof(a, s, s, h, a.key(rng.choice(ROOFS)), a.key("8a3a28"), 0.6, 0.4)
        _new("tower", str(i), a, (s + 2, s + 2))


def build_public(rng):
    # 0 basilica: long hall, clerestory, gabled roof, colonnade front
    a = Acc("public0")
    w, d = 46, 22
    a.box((0, 0, 7), (w, d, 14), a.key("efe3cc"))
    a.box((0, 0, 16), (w - 6, d - 8, 4), a.key("f2e6d2"))
    for k in range(10):
        a.box((-w / 2 + 6 + k * (w - 12) / 9, (d - 8) / 2 + 0.02, 16), (1.4, 0.05, 1.8), a.key("5e4038"))
    a.T = Matrix.Translation((0, 0, 0))
    T.hip_roof(a, w, d, 14, a.key(T.ROOF), a.key("8a3a28"), 0.6, 0.12)
    roof(a, "gable_x", w - 6, d - 8, 18, rng, T.ROOF)
    for k in range(12):
        x = -w / 2 + 2 + k * (w - 4) / 11
        a.stack([(0, ring(10, 0.55, 0.55, 0.04), x, d / 2 + 2.4), (9, ring(10, 0.46, 0.46, 0.04), x, d / 2 + 2.4)], a.key(MARBLE))
    a.box((0, d / 2 + 2.4, 9.5), (w + 1, 1.6, 1.0), a.key(MARBLE))
    a.poly([(-w / 2, d / 2 + 0.02, 0.2), (w / 2, d / 2 + 0.02, 0.2), (w / 2, d / 2 + 0.02, 8.6), (-w / 2, d / 2 + 0.02, 8.6)][::-1], a.key("8a6a5e"))
    _new("public", "basilica", a, (w + 2, d + 8))
    # 1 baths: a block with three domes
    a = Acc("public1")
    a.box((0, 0, 6), (40, 30, 12), a.key("e6cdb0"))
    a.box((0, 0, 11.9), (41, 31, 0.4), a.key(MARBLE))
    for (x, y, r) in ((-12, 0, 6), (0, 2, 9), (12, 0, 6)):
        a.stack([(12, ring(14, r, r), x, y), (12 + r * 0.5, ring(14, r, r), x, y)], a.key("efe3cc"), False, False)
        a.stack([(12 + r * 0.5 + math.sin(t * math.pi / 2) * r * 0.8, ring(14, max(0.3, math.cos(t * math.pi / 2) * r * 1.03), max(0.3, math.cos(t * math.pi / 2) * r * 1.03)), x, y)
                 for t in (0, 0.35, 0.65, 0.88, 1.0)], a.key("b8a890"), False, True)
    for k in range(8):
        x = -18 + k * 5.2
        pts = [(x - 1.4, 15.03, 1.0), (x + 1.4, 15.03, 1.0)] + [(x + math.cos(math.pi * q / 5) * 1.4, 15.03, 6 + math.sin(math.pi * q / 5) * 1.4) for q in range(6)]
        a.poly(pts, a.key("5e4038"))
    _new("public", "baths", a, (42, 32))
    # 2 theatre: half ring of seating with a stage building
    a = Acc("public2")
    r = 26
    for k in range(4):
        rr = r - k * 4
        a.stack([(k * 3.0, [(math.cos(math.pi * q / 16) * rr, -math.sin(math.pi * q / 16) * rr) for q in range(17)] + [(-(rr - 4), 0.0), (rr - 4, 0.0)][::-1], 0, 0),
                 ((k + 1) * 3.0, [(math.cos(math.pi * q / 16) * rr, -math.sin(math.pi * q / 16) * rr) for q in range(17)] + [(-(rr - 4), 0.0), (rr - 4, 0.0)][::-1], 0, 0)],
                a.key(MARBLE2 if k % 2 else "e6dac4"))
    a.box((0, 4, 6), (2 * r + 4, 5, 12), a.key("e8d6ba"))
    for k in range(9):
        a.stack([(0.3, ring(8, 0.4, 0.4), -r + 4 + k * (2 * r - 8) / 8, 1.0), (9, ring(8, 0.35, 0.35), -r + 4 + k * (2 * r - 8) / 8, 1.0)], a.key(MARBLE))
    T.hip_roof(a, 2 * r + 4, 5, 12, a.key(T.ROOF), a.key("8a3a28"), 0.4, 0.2)
    _new("public", "theatre", a, (2 * r + 6, r + 10))
    # 3 stoa / market: a long two-storey colonnade
    a = Acc("public3")
    w = 50
    a.box((0, -3, 5), (w, 6, 10), a.key("eddabe"))
    for fl in range(2):
        for k in range(16):
            x = -w / 2 + 1.5 + k * (w - 3) / 15
            a.stack([(fl * 5, ring(8, 0.4, 0.4), x, 1.5), (fl * 5 + 4.4, ring(8, 0.34, 0.34), x, 1.5)], a.key(MARBLE))
        a.box((0, 0, fl * 5 + 4.7), (w + 0.6, 4.0, 0.6), a.key(MARBLE))
    a.poly([(-w / 2, 0.02, 0.1), (w / 2, 0.02, 0.1), (w / 2, 0.02, 9.6), (-w / 2, 0.02, 9.6)][::-1], a.key("8a6a5e"))
    roof(a, "gable_x", w, 10, 10, rng, T.ROOF)
    for k in range(4):
        banner_flat(a, (-w / 2 + 8 + k * (w - 16) / 3, 1.8, 9.2), 2.2, 4.5, math.pi)
    _new("public", "stoa", a, (w + 2, 12))
    # 4 rotunda with a portico (a pantheon)
    a = Acc("public4")
    r = 15
    a.stack([(0, ring(18, r, r), 0, 0), (14, ring(18, r, r), 0, 0)], a.key("e6cdb0"), False, False)
    a.stack([(14 + math.sin(t * math.pi / 2) * r * 0.85, ring(18, max(0.4, math.cos(t * math.pi / 2) * r * 1.02), max(0.4, math.cos(t * math.pi / 2) * r * 1.02)), 0, 0)
             for t in (0, 0.3, 0.55, 0.78, 0.94, 1.0)], a.key("b8a890"), False, True)
    a.T = Matrix.Translation((0, r + 5, 0)) @ Matrix.Rotation(math.pi, 4, "Z")
    temple(a, 20, 10, 11, rng, False)
    _new("public", "rotunda", a, (2 * r + 2, 2 * r + 16))


def build_arches(rng):
    for i in range(4):
        a = Acc("arch%d" % i)
        if i == 0:
            T.arch(a, 0, 0, 0, 0.0, 9, 9, 3)
            dims = (10, 4)
        elif i == 1:
            T.arch(a, 0, 0, 0, 0.0, 16, 14, 5)
            for sx in (-1, 1):
                T.arch(a, sx * 10, 0, 0, 0.0, 6, 9, 4)
            dims = (28, 6)
        elif i == 2:
            # a city gate between two round towers
            T.arch(a, 0, 0, 0, 0.0, 10, 11, 6)
            for sx in (-1, 1):
                a.stack([(0, ring(12, 4.5, 4.5), sx * 9, 0), (18, ring(12, 4.5, 4.5), sx * 9, 0)], a.key("e2c7a2"), True, True)
                for k in range(8):
                    ang = 2 * math.pi * k / 8
                    a.box((sx * 9 + math.cos(ang) * 4.6, math.sin(ang) * 4.6, 18.5), (1.0, 1.0, 1.0), a.key("e2c7a2"))
            dims = (28, 10)
        else:
            T.aqueduct(a, (-30, 0, 0), (30, 0, 0), 0, 26)
            dims = (62, 4)
        _new("arch", str(i), a, dims)


def build_monuments(rng):
    a = Acc("mon0")
    a.box((0, 0, 1.5), (4, 4, 3), a.key(MARBLE2))
    a.stack([(3, ring(12, 1.3, 1.3, 0.05), 0, 0), (24, ring(12, 1.15, 1.15, 0.05), 0, 0)], a.key(MARBLE))
    for k in range(7):
        a.stack([(4 + k * 2.9, ring(12, 1.32, 1.32), 0, 0), (4.3 + k * 2.9, ring(12, 1.32, 1.32), 0, 0)], a.key(MARBLE2))
    a.box((0, 0, 24.5), (3, 3, 1), a.key(MARBLE))
    a.tube([(0, 0, 25), (0, 0, 28.5)], [0.7, 0.5], a.key(GOLD, 0.45, 0.5), 6)
    a.cone((0, 0, 28.4), 0.55, 1.0, a.key(GOLD, 0.45, 0.5), 6)
    _new("monument", "column", a, (6, 6))
    a = Acc("mon1")
    a.box((0, 0, 1.0), (4.5, 4.5, 2), a.key(MARBLE2))
    a.box((0, 0, 2.5), (3.2, 3.2, 1), a.key(MARBLE))
    a.stack([(3, [(-1.1, -1.1), (1.1, -1.1), (1.1, 1.1), (-1.1, 1.1)], 0, 0), (19, [(-0.7, -0.7), (0.7, -0.7), (0.7, 0.7), (-0.7, 0.7)], 0, 0)], a.key("d9c4a0"))
    a.cone((0, 0, 19), 0.99, 1.6, a.key(GOLD, 0.45, 0.5), 4)
    _new("monument", "obelisk", a, (6, 6))
    a = Acc("mon2")
    a.stack([(0, ring(10, 7, 7), 0, 0), (1.1, ring(10, 7, 7), 0, 0)], a.key(MARBLE))
    a.stack([(0.9, ring(10, 6.4, 6.4), 0, 0), (0.95, ring(10, 6.4, 6.4), 0, 0)], a.key("5aa3c4", 0.05))
    a.stack([(0.9, ring(8, 1.5, 1.5), 0, 0), (3.2, ring(8, 1.1, 1.1), 0, 0)], a.key(MARBLE2))
    a.stack([(3.1, ring(10, 1.2, 1.2), 0, 0), (3.5, ring(10, 3.0, 3.0), 0, 0)], a.key(MARBLE))
    a.stack([(3.5, ring(6, 0.5, 0.5), 0, 0), (6.5, ring(6, 0.35, 0.35), 0, 0)], a.key(MARBLE))
    a.cone((0, 0, 6.5), 0.6, 1.3, a.key(GOLD, 0.45, 0.5), 6)
    _new("monument", "fountain", a, (15, 15))


def build_trees(rng):
    for i, (h, kind) in enumerate(((9, "cypress"), (13, "cypress"), (6.5, "cypress"), (10, "pine"))):
        a = Acc("tree%d" % i)
        tree(a, (0, 0, 0), h, kind)
        if i == 2:
            tree(a, (1.4, 0.8, 0), h * 0.85, "cypress")
            tree(a, (-1.1, 1.3, 0), h * 0.7, "cypress")
        _new("tree", str(i), a, (3, 3))


def build_lod(rng):
    """Simplified buildings for the middle and far distance: massing, cornice, window bands, roofs."""
    for i in range(8):
        a = Acc("mid%d" % i)
        w, d = rng.uniform(10, 22), rng.uniform(10, 22)
        fl = rng.choice((2, 2, 3, 3, 4))
        h = fl * 3.3 + 0.5
        a.box((0, 0, h / 2), (w, d, h), a.key(rng.choice(WALLS)))
        a.box((0, 0, h - 0.15), (w + 0.4, d + 0.4, 0.3), a.key(MARBLE))
        for f in range(fl):
            for side in range(4):
                ang = side * math.pi / 2
                L = w if side % 2 == 0 else d
                D = d if side % 2 == 0 else w
                a.box((math.sin(ang) * (D / 2 + 0.02), -math.cos(ang) * (D / 2 + 0.02), 1.9 + f * 3.3), (L * 0.75, 0.05, 1.0), a.key("7a5a50"), ang)
        if i % 4 == 3:
            keep = a.T
            a.T = a.T @ Matrix.Translation((w * 0.4, d * 0.3, 0))
            a.box((0, 0, (h + 6) / 2), (w * 0.4, d * 0.4, h + 6), a.key(rng.choice(WALLS)))
            T.hip_roof(a, w * 0.4, d * 0.4, h + 6, a.key(rng.choice(ROOFS)), a.key("8a3a28"), 0.4, 0.2)
            a.T = keep
        roof(a, ["hip", "gable_x", "gable_y", "hip", "flat", "hip", "gable_x", "hip"][i], w, d, h, rng, rng.choice(ROOFS))
        _new("mid", str(i), a, (w + 2, d + 2))
    for i in range(6):
        a = Acc("far%d" % i)
        w, d = rng.uniform(12, 30), rng.uniform(12, 30)
        h = rng.uniform(6, 18)
        a.box((0, 0, h / 2), (w, d, h), a.key(rng.choice(WALLS)))
        T.hip_roof(a, w, d, h, a.key(rng.choice(ROOFS)), a.key("8a3a28"), 0.5, rng.uniform(0.13, 0.19))
        _new("far", str(i), a, (w + 2, d + 2))
    # skyline landmarks for the far distance
    a = Acc("sky0")
    a.stack([(0, ring(12, 22, 22), 0, 0), (20, ring(12, 22, 22), 0, 0)], a.key("e6cdb0"), False, False)
    a.stack([(20 + math.sin(t * math.pi / 2) * 18, ring(12, max(0.5, math.cos(t * math.pi / 2) * 22.5), max(0.5, math.cos(t * math.pi / 2) * 22.5)), 0, 0) for t in (0, 0.35, 0.65, 0.88, 1.0)],
            a.key("c99a45", 0.5, 0.4), False, True)
    _new("skyline", "dome", a, (46, 46))
    a = Acc("sky1")
    a.box((0, 0, 28), (11, 11, 56), a.key("e2c7a2"))
    T.hip_roof(a, 11, 11, 56, a.key(T.ROOF), a.key("8a3a28"), 0.6, 0.35)
    _new("skyline", "tower", a, (13, 13))
    a = Acc("sky2")
    a.T = Matrix.Rotation(math.pi, 4, "Z")
    temple(a, 28, 40, 14, rng, False)
    _new("skyline", "temple", a, (32, 46))


def build_library(seed=7):
    R.clear("Asset Library")
    LIB.clear()
    rng = random.Random(seed)
    build_residential(rng)
    build_temples(rng)
    build_towers(rng)
    build_public(rng)
    build_arches(rng)
    build_monuments(rng)
    build_trees(rng)
    build_lod(rng)
    lc = bpy.data.collections.get("Asset Library")
    for lcoll in bpy.context.view_layer.layer_collection.children:
        if lcoll.collection == lc:
            lcoll.exclude = False
    print("asset library:", {k: len(v) for k, v in LIB.items()})
    return LIB
