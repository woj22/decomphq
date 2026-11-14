"""The Palatium Ardens, hand-placed low-poly, starting with its hub: the Peristyle of the Sun.

Run:  python3 imperium/blender/palace.py [--samples N] [--no-people]
Writes renders/palace_*.png and assets/palace/peristyle.glb.

Architecture kit: every piece is built from explicit sections (8- to 16-sided where round, planar
elsewhere), flat colours, the same style as the cast. Layout in metres: the courtyard spans
x, y in [-18, 18]; the character-facing direction -Y is "north" (toward the Council Chamber).
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

import kharad as K  # noqa: E402
import cast as C  # noqa: E402
from cast import block, done, m, mesh_from, metal, pyramid, ringN, shell, spike, stack, tube  # noqa: E402

ROOT = K.ROOT
MARBLE = "e8e0d0"
MARBLE2 = "d3c7b1"
MARBLE3 = "b9ab92"
PLASTER = "d9b98e"
OCHRE = "b0563c"
ROOF = "b5523a"
GOLD = C.GOLD
GRASS = "6f8f45"
HEDGE = "4d6b34"
CYPRESS = "355230"
WATER = "4f97b3"
CRIMSON = "8e1f24"
BRONZE = "8a5a2a"

H = 18.0      # half size of the courtyard
COL = 14.0    # colonnade line
WALL_H = 8.6
COL_H = 6.4


def col_(hexcol, rough=0.85):
    return m(hexcol, rough)


# ----------------------------------------------------------------------------- kit pieces
def quad_floor(name, x0, y0, x1, y1, z, tile, ca, cb):
    vs, fa, fb = [], [], []
    nx, ny = int(round((x1 - x0) / tile)), int(round((y1 - y0) / tile))
    for i in range(nx):
        for j in range(ny):
            ax, ay = x0 + i * tile, y0 + j * tile
            b = len(vs)
            vs += [(ax, ay, z), (ax + tile, ay, z), (ax + tile, ay + tile, z), (ax, ay + tile, z)]
            ((fa if (i + j) % 2 == 0 else fb)).append((b, b + 1, b + 2, b + 3))
    o = mesh_from(name, vs, fa + fb, False)
    done(o, col_(ca), lambda c, n: 0, [col_(cb)])
    # second colour for the alternate tiles
    k = len(fa)
    for idx, p in enumerate(o.data.polygons):
        p.material_index = 0 if idx < k else 1
    return o


def column(x, y, h=COL_H, r=0.38, shaft=MARBLE):
    parts = []
    parts.append(done(block("ColBase", (x, y, 0.15), (r * 2.6, r * 2.6, 0.3)), col_(MARBLE2)))
    parts.append(done(stack("ColTorus", [(0.3, ringN(12, r * 1.25, r * 1.25), x, y), (0.42, ringN(12, r * 1.18, r * 1.18), x, y),
                                         (0.5, ringN(12, r * 1.05, r * 1.05), x, y)]), col_(MARBLE)))
    fl = 0.045
    parts.append(done(stack("ColShaft", [(0.5, ringN(16, r, r, fl), x, y), (0.5 + (h - 1.3) * 0.35, ringN(16, r * 0.98, r * 0.98, fl), x, y),
                                         (h - 0.8, ringN(16, r * 0.86, r * 0.86, fl), x, y)], cap_bottom=False, cap_top=False), col_(shaft)))
    parts.append(done(stack("ColNeck", [(h - 0.8, ringN(12, r * 0.9, r * 0.9), x, y), (h - 0.62, ringN(12, r * 1.08, r * 1.08), x, y)]), metal(GOLD)))
    parts.append(done(block("ColEchinus", (x, y, h - 0.48), (r * 2.5, r * 1.6, 0.26)), col_(MARBLE)))
    for sx in (1, -1):
        parts.append(done(tube("Volute", [(x + sx * r * 1.15, y - r * 0.85, h - 0.46), (x + sx * r * 1.15, y + r * 0.85, h - 0.46)], [0.17, 0.17], 8), col_(MARBLE)))
        parts.append(done(tube("VoluteEye", [(x + sx * r * 1.15, y - r * 0.9, h - 0.46), (x + sx * r * 1.15, y + r * 0.9, h - 0.46)], [0.07, 0.07], 6), metal(GOLD)))
    parts.append(done(block("ColAbacus", (x, y, h - 0.15), (r * 2.8, r * 2.8, 0.3)), col_(MARBLE)))
    return parts


def entablature(a, b, z, depth=1.1):
    a, b = Vector(a), Vector(b)
    mid = (a + b) / 2
    ln = (b - a).length + depth
    rot = (0, 0, math.atan2(b.y - a.y, b.x - a.x))
    return [done(block("Architrave", (mid.x, mid.y, z + 0.3), (ln, depth, 0.6), rot), col_(MARBLE)),
            done(block("Frieze", (mid.x, mid.y, z + 0.78), (ln, depth * 0.92, 0.36), rot), col_(CRIMSON)),
            done(block("FriezeGold", (mid.x, mid.y, z + 0.62), (ln + 0.02, depth * 0.94, 0.06), rot), metal(GOLD)),
            done(block("Cornice", (mid.x, mid.y, z + 1.08), (ln + 0.2, depth + 0.3, 0.24), rot), col_(MARBLE))]


def lean_roof(a, b, out, depth, z_low, rise):
    """A terracotta lean-to roof strip rising from the line a-b toward `out`, with tile ridges."""
    a, b = Vector((a[0], a[1], z_low)), Vector((b[0], b[1], z_low))
    o = Vector(out).normalized() * depth + Vector((0, 0, rise))
    parts = [done(mesh_from("Roof", [tuple(a), tuple(b), tuple(b + o), tuple(a + o)], [(0, 1, 2, 3)], False), col_(ROOF))]
    under = mesh_from("RoofUnder", [tuple(b + Vector((0, 0, -0.15))), tuple(a + Vector((0, 0, -0.15))), tuple(a + o + Vector((0, 0, -0.15))), tuple(b + o + Vector((0, 0, -0.15)))],
                      [(0, 1, 2, 3)], False)
    parts.append(done(under, col_("6b4a2e")))
    n = int((b - a).length / 0.55)
    for i in range(n + 1):
        p = a.lerp(b, i / n)
        parts.append(done(tube("TileRow", [tuple(p + Vector((0, 0, 0.06))), tuple(p + o + Vector((0, 0, 0.06)))], [0.09, 0.09], 4, 0.6), col_("9c4330")))
    return parts


def wall(a, b, h, doors=(), thick=0.7):
    """A plastered wall from a to b with a marble plinth, a frieze band, a cornice, and door gaps."""
    a, b = Vector(a), Vector(b)
    d = b - a
    ln = d.length
    u = d.normalized()
    rot = (0, 0, math.atan2(d.y, d.x))
    cuts = [[0.0, ln]]
    for (off, w) in doors:
        nc = []
        for s0, s1 in cuts:
            if off - w / 2 > s0 and off + w / 2 < s1:
                nc += [[s0, off - w / 2], [off + w / 2, s1]]
            else:
                nc.append([s0, s1])
        cuts = nc
    parts = []
    for s0, s1 in cuts:
        c = a + u * ((s0 + s1) / 2)
        L = s1 - s0
        parts.append(done(block("Wall", (c.x, c.y, h / 2), (L, thick, h), rot), col_(PLASTER)))
        parts.append(done(block("Plinth", (c.x, c.y, 0.5), (L, thick + 0.12, 1.0), rot), col_(MARBLE2)))
        parts.append(done(block("Band", (c.x, c.y, 3.4), (L, thick + 0.06, 0.18), rot), col_(MARBLE)))
        parts.append(done(block("UpperBand", (c.x, c.y, h - 1.1), (L, thick + 0.04, 0.9), rot), col_(OCHRE)))
        parts.append(done(block("WallCornice", (c.x, c.y, h - 0.15), (L, thick + 0.35, 0.3), rot), col_(MARBLE)))
    for (off, w) in doors:
        c = a + u * off
        parts += doorway(c, rot, w, h, thick)
    return parts


def doorway(c, rot, w, h, thick, dh=5.0, open_=False):
    """A monumental doorway: marble jambs, a lintel, a pediment, bronze doors (or a dark opening)."""
    parts = []
    R = Euler(rot).to_matrix()
    def at(x, y, z):
        return tuple(Vector((c.x, c.y, 0)) + R @ Vector((x, y, z)))
    for sx in (1, -1):
        parts.append(done(block("Jamb", at(sx * (w / 2 + 0.3), 0, dh / 2), (0.6, thick + 0.3, dh), rot), col_(MARBLE)))
        parts.append(done(block("Pilaster", at(sx * (w / 2 + 0.75), -thick / 2 - 0.12, dh / 2 + 0.4), (0.5, 0.25, dh + 0.8), rot), col_(MARBLE)))
    parts.append(done(block("Lintel", at(0, 0, dh + 0.35), (w + 2.2, thick + 0.4, 0.7), rot), col_(MARBLE)))
    parts.append(done(block("DoorWall", at(0, 0, (dh + 0.7 + h) / 2), (w + 0.1, thick, h - dh - 0.7), rot), col_(PLASTER)))
    # pediment
    for side in (-1, 1):
        y = side * (thick / 2 + 0.18)
        tri = [at(-(w / 2 + 1.1), y, dh + 0.7), at(w / 2 + 1.1, y, dh + 0.7), at(0, y, dh + 1.9)]
        parts.append(done(mesh_from("Pediment", tri if side > 0 else list(reversed(tri)), [(0, 1, 2)], False), col_(MARBLE)))
        parts.append(done(mesh_from("Tympanum", [at(-(w / 2 + 0.7), y * 1.05, dh + 0.85), at(w / 2 + 0.7, y * 1.05, dh + 0.85), at(0, y * 1.05, dh + 1.65)]
                                    if side > 0 else [at(w / 2 + 0.7, y * 1.05, dh + 0.85), at(-(w / 2 + 0.7), y * 1.05, dh + 0.85), at(0, y * 1.05, dh + 1.65)],
                                    [(0, 1, 2)], False), col_(CRIMSON)))
    for sx in (1, -1):
        p0, p1 = at(sx * (w / 2 + 1.2), 0, dh + 0.68), at(0, 0, dh + 1.98)
        parts.append(done(tube("Raking", [p0, p1], [0.16, 0.16], 4), col_(MARBLE)))
    parts.append(done(pyramid("Acroterion", [at(-0.25, -0.15, dh + 1.95), at(0.25, -0.15, dh + 1.95), at(0.25, 0.15, dh + 1.95), at(-0.25, 0.15, dh + 1.95)],
                              at(0, 0, dh + 2.6)), metal(GOLD)))
    if open_:
        parts.append(done(block("Dark", at(0, 0.05, dh / 2), (w, 0.1, dh), rot), col_("1c1412")))
    else:
        for sx in (1, -1):
            parts.append(done(block("Door", at(sx * w / 4, 0, dh / 2), (w / 2 - 0.04, 0.14, dh), rot), metal(BRONZE)))
            for k in range(3):
                parts.append(done(block("DoorPanel", at(sx * w / 4, -0.09, 0.9 + k * 1.4), (w / 2 - 0.5, 0.05, 1.1), rot), metal("a8742f")))
            parts.append(done(tube("Ring", [at(sx * 0.35, -0.12, 2.4), at(sx * 0.35, -0.2, 2.4)], [0.12, 0.12], 8), metal(GOLD)))
    return parts


def banner(x, y, facing_yaw, top, length=3.6, width=1.4):
    """A crimson swallowtail banner with a gold laurel, hung from a gilded rod."""
    R = Euler((0, 0, facing_yaw)).to_matrix()
    c = Vector((x, y, top))
    def at(px, pz, py=0.0):
        return tuple(c + R @ Vector((px, py, pz)))
    hw, tail = width / 2, width * 0.45
    body = length - tail
    parts = [done(tube("Rod", [at(-hw - 0.25, 0.08, -0.12), at(hw + 0.25, 0.08, -0.12)], [0.05, 0.05], 6), metal(GOLD))]
    cloth = mesh_from("Banner", [at(-hw, 0), at(hw, 0), at(hw, -body), at(0, -length), at(-hw, -body)], [(4, 3, 2, 1, 0)], False)
    s = cloth.modifiers.new("sol", "SOLIDIFY")
    s.thickness = 0.04
    K.apply_all(cloth)
    parts.append(done(cloth, col_(CRIMSON)))
    for sx in (1, -1):
        parts.append(done(block("BTrim", at(sx * (hw - 0.07), -body / 2, -0.03), (0.07, 0.02, body - 0.1), (0, 0, facing_yaw)), metal(GOLD)))
    # laurel wreath: two arcs of leaf diamonds
    for sx in (1, -1):
        for i in range(7):
            a = -1.2 + i * 0.4
            px, pz = sx * math.cos(a) * 0.36 * width / 1.4, -body * 0.45 + math.sin(a) * 0.36 * width / 1.4
            lf = mesh_from("Leaf", [at(px - 0.05, pz, -0.035), at(px, pz + 0.09, -0.035), at(px + 0.05, pz, -0.035), at(px, pz - 0.06, -0.035)], [(3, 2, 1, 0)], False)
            parts.append(done(lf, metal(GOLD)))
    return parts


def brazier(x, y, z=0.0, s=1.0, light=True):
    parts = []
    for i in range(3):
        a = 2 * math.pi * i / 3
        parts.append(done(tube("Leg", [(x + math.cos(a) * 0.45 * s, y + math.sin(a) * 0.45 * s, z), (x + math.cos(a) * 0.2 * s, y + math.sin(a) * 0.2 * s, z + 1.0 * s)],
                               [0.05 * s, 0.04 * s], 4), metal(BRONZE)))
    parts.append(done(stack("Bowl", [(z + 0.95 * s, ringN(8, 0.2 * s, 0.2 * s), x, y), (z + 1.2 * s, ringN(8, 0.6 * s, 0.6 * s), x, y),
                                     (z + 1.27 * s, ringN(8, 0.62 * s, 0.62 * s), x, y)], cap_top=False), metal("a8742f")))
    fire = m("ff8a2a", 0.5, 0, "ff6a10", 2.2)
    core = m("ffd36a", 0.5, 0, "ffb030", 3.0)
    for i in range(6):
        a = 2 * math.pi * i / 6
        h = (0.6 + 0.3 * (i % 2)) * s
        base = [(x + math.cos(a) * 0.26 * s + math.cos(a + k * 2.1) * 0.12 * s, y + math.sin(a) * 0.26 * s + math.sin(a + k * 2.1) * 0.12 * s, z + 1.15 * s) for k in range(3)]
        parts.append(done(pyramid("Flame", base, (x + math.cos(a) * 0.15 * s, y + math.sin(a) * 0.15 * s, z + 1.15 * s + h)), fire))
    parts.append(done(pyramid("FlameCore", [(x + math.cos(k * 2.1) * 0.22 * s, y + math.sin(k * 2.1) * 0.22 * s, z + 1.15 * s) for k in range(3)], (x, y, z + 2.1 * s)), core))
    if light:
        bpy.ops.object.light_add(type="POINT", location=(x, y, z + 1.9 * s))
        l = bpy.context.active_object
        l.data.energy = 260 * s
        l.data.color = (1.0, 0.62, 0.3)
        l.data.shadow_soft_size = 0.4
    return parts


def cypress(x, y, h=6.0, z=0.0):
    return [done(tube("Trunk", [(x, y, z), (x, y, z + 0.6)], [0.14, 0.12], 5), col_("5a3e28")),
            done(stack("Cypress", [(z + 0.4, ringN(7, h * 0.1, h * 0.1, 0.12), x, y), (z + h * 0.35, ringN(7, h * 0.15, h * 0.15, 0.14), x, y),
                                   (z + h * 0.75, ringN(7, h * 0.1, h * 0.1, 0.12), x, y), (z + h, ringN(7, 0.05, 0.05), x, y)]), col_(CYPRESS))]


def urn(x, y, z=0.0):
    return [done(stack("Urn", [(z, ringN(8, 0.28, 0.28), x, y), (z + 0.3, ringN(8, 0.42, 0.42), x, y), (z + 0.62, ringN(8, 0.36, 0.36), x, y),
                               (z + 0.72, ringN(8, 0.44, 0.44), x, y)], cap_top=True), col_("b3643c")),
            done(stack("Shrub", [(z + 0.7, ringN(7, 0.42, 0.42, 0.1), x, y), (z + 1.05, ringN(7, 0.55, 0.55, 0.12), x, y), (z + 1.45, ringN(7, 0.2, 0.2), x, y)]), col_(HEDGE))]


def statue(spec, x, y, yaw, pedestal=1.6):
    marble = dict(spec)
    for k in ("skin", "hair", "primary", "secondary", "trim", "cloak", "shield", "lining"):
        if marble.get(k):
            marble[k] = MARBLE
    parts = [done(block("Pedestal", (x, y, pedestal / 2), (1.3, 1.3, pedestal)), col_(MARBLE2)),
             done(block("PedCap", (x, y, pedestal - 0.08), (1.5, 1.5, 0.16)), col_(MARBLE)),
             done(block("PedFoot", (x, y, 0.1), (1.55, 1.55, 0.2)), col_(MARBLE))]
    fig = C.Figure("statue", marble).build()
    for o in fig:
        o.data.materials.clear()
        o.data.materials.append(col_(MARBLE, 0.6))
        for p in o.data.polygons:
            p.material_index = 0
    place(fig, (x, y, pedestal), yaw, 1.25)
    return parts + fig


def place(objs, loc, yaw, scale=1.0):
    e = bpy.data.objects.new("Group", None)
    bpy.context.collection.objects.link(e)
    for o in objs:
        o.parent = e
    e.location = loc
    e.rotation_euler = (0, 0, yaw)
    e.scale = (scale, scale, scale)
    return e


def hip_roof(cx, cy, w, d, z, rise, col=ROOF):
    """A hipped roof over a wing seen beyond the courtyard walls."""
    ridge = max(w - d, 0.2) / 2 if w >= d else 0.0
    ridge_y = max(d - w, 0.2) / 2 if d > w else 0.0
    vs = [(cx - w / 2, cy - d / 2, z), (cx + w / 2, cy - d / 2, z), (cx + w / 2, cy + d / 2, z), (cx - w / 2, cy + d / 2, z),
          (cx - ridge, cy - ridge_y, z + rise), (cx + ridge, cy + ridge_y, z + rise)]
    if w >= d:
        fs = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
    else:
        fs = [(1, 2, 5, 4), (3, 0, 4, 5), (0, 1, 4), (2, 3, 5)]
    return [done(mesh_from("HipRoof", vs, fs), col_(col)),
            done(block("Eave", (cx, cy, z - 0.15), (w + 0.2, d + 0.2, 0.3)), col_(MARBLE))]


def dome(cx, cy, z, r):
    parts = [done(stack("Drum", [(z, ringN(16, r * 1.05, r * 1.05), cx, cy), (z + r * 0.45, ringN(16, r * 1.05, r * 1.05), cx, cy)], cap_bottom=False), col_(PLASTER))]
    for i in range(16):
        a = 2 * math.pi * i / 16
        parts.append(done(block("DrumPilaster", (cx + math.cos(a) * r * 1.08, cy + math.sin(a) * r * 1.08, z + r * 0.22), (0.5, 0.5, r * 0.45), (0, 0, a)), col_(MARBLE)))
    secs = []
    for k in range(6):
        t = k / 5
        ang = t * math.pi / 2
        secs.append((z + r * 0.45 + math.sin(ang) * r * 0.9, ringN(16, max(0.3, math.cos(ang) * r), max(0.3, math.cos(ang) * r)), cx, cy))
    parts.append(done(stack("Dome", secs, cap_bottom=False), metal("c99a45")))
    for i in range(16):
        a = 2 * math.pi * i / 16
        pts = [(cx + math.cos(a) * r * 1.0, cy + math.sin(a) * r * 1.0, z + r * 0.46), (cx + math.cos(a) * 0.4, cy + math.sin(a) * 0.4, z + r * 1.33)]
        parts.append(done(tube("Rib", pts, [0.18, 0.12], 4), col_(MARBLE)))
    top = z + r * 1.35
    parts.append(done(stack("Lantern", [(top, ringN(8, 0.9, 0.9), cx, cy), (top + 1.6, ringN(8, 0.9, 0.9), cx, cy), (top + 2.0, ringN(8, 1.1, 1.1), cx, cy)]), col_(MARBLE)))
    parts.append(done(pyramid("Finial", [(cx + math.cos(i * 2 * math.pi / 6) * 0.5, cy + math.sin(i * 2 * math.pi / 6) * 0.5, top + 2.0) for i in range(6)], (cx, cy, top + 3.6)), metal(GOLD)))
    return parts


# ----------------------------------------------------------------------------- the courtyard
def build_peristyle():
    P = []
    # floors: marble portico, raised garden, cross paths, the plaza
    P.append(quad_floor("PorticoFloor", -H, -H, H, H, 0.0, 2.0, "e3d6bf", "c7b49b"))
    P.append(done(block("Garden", (0, 0, 0.1), (COL * 2 - 1.0, COL * 2 - 1.0, 0.2)), col_(MARBLE2)))
    for sx in (1, -1):
        for sy in (1, -1):
            for (cx, cy, w, d) in ((8.6, 4.2, 9.6, 5.2), (4.2, 9.6, 5.2, 7.6)):
                x, y = sx * cx, sy * cy
                P.append(done(block("Lawn", (x, y, 0.25), (w, d, 0.12)), col_(GRASS)))
                P.append(done(stack("Hedge", [(0.3, [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)], x, y),
                                              (0.6, [(-w / 2 + 0.05, -d / 2 + 0.05), (w / 2 - 0.05, -d / 2 + 0.05), (w / 2 - 0.05, d / 2 - 0.05), (-w / 2 + 0.05, d / 2 - 0.05)], x, y)],
                                        cap_bottom=False, cap_top=False), col_(HEDGE)))
    P.append(quad_floor("Plaza", -6, -6, 6, 6, 0.205, 1.5, "efe6d2", "d8cbb1"))
    for sx in (1, -1):
        P.append(quad_floor("PathEW", 6 if sx > 0 else -COL + 0.5, -1.5, COL - 0.5 if sx > 0 else -6, 1.5, 0.205, 1.5, "efe6d2", "d8cbb1"))
        P.append(quad_floor("PathNS", -1.5, 6 if sx > 0 else -COL + 0.5, 1.5, COL - 0.5 if sx > 0 else -6, 0.205, 1.5, "efe6d2", "d8cbb1"))
    # the fountain of the sun
    P.append(done(stack("Basin", [(0.2, ringN(8, 3.6, 3.6, 0, math.pi / 8), 0, 0), (0.95, ringN(8, 3.6, 3.6, 0, math.pi / 8), 0, 0),
                                  (0.95, ringN(8, 3.25, 3.25, 0, math.pi / 8), 0, 0), (0.5, ringN(8, 3.25, 3.25, 0, math.pi / 8), 0, 0)],
                            cap_bottom=False, cap_top=False), col_(MARBLE)))
    P.append(done(block("BasinRim", (0, 0, 0.98), (0.01, 0.01, 0.01)), col_(MARBLE)))
    water = m(WATER, 0.05, 0.0)
    P.append(done(stack("Water", [(0.82, ringN(8, 3.28, 3.28, 0, math.pi / 8), 0, 0), (0.83, ringN(8, 3.28, 3.28, 0, math.pi / 8), 0, 0)]), water))
    P.append(done(stack("Pedestal", [(0.5, ringN(8, 0.8, 0.8), 0, 0), (2.2, ringN(8, 0.55, 0.55), 0, 0)]), col_(MARBLE)))
    P.append(done(stack("UpperBowl", [(2.1, ringN(10, 0.6, 0.6), 0, 0), (2.5, ringN(10, 1.7, 1.7), 0, 0), (2.62, ringN(10, 1.75, 1.75), 0, 0)]), col_(MARBLE)))
    P.append(done(stack("UpperWater", [(2.58, ringN(10, 1.6, 1.6), 0, 0), (2.6, ringN(10, 1.6, 1.6), 0, 0)]), water))
    for i in range(0):
        a = 2 * math.pi * i / 8
        P.append(done(tube("Spout", [(math.cos(a) * 1.65, math.sin(a) * 1.65, 2.55), (math.cos(a) * 2.6, math.sin(a) * 2.6, 1.6), (math.cos(a) * 2.9, math.sin(a) * 2.9, 0.86)],
                           [0.06, 0.05, 0.08], 4), m("9fd4e6", 0.05)))
    P.append(done(stack("Spire", [(2.6, ringN(6, 0.3, 0.3), 0, 0), (3.8, ringN(6, 0.2, 0.2), 0, 0)]), col_(MARBLE)))
    # golden sun on top
    sun_c = Vector((0, 0, 4.4))
    P.append(done(stack("SunDisc", [(sun_c.z - 0.06, ringN(12, 0.55, 0.55), 0, 0), (sun_c.z + 0.06, ringN(12, 0.55, 0.55), 0, 0)]), metal(GOLD)))
    for i in range(12):
        a = 2 * math.pi * i / 12
        P.append(done(pyramid("SunRay", [(math.cos(a - 0.15) * 0.5, math.sin(a - 0.15) * 0.5, sun_c.z), (math.cos(a + 0.15) * 0.5, math.sin(a + 0.15) * 0.5, sun_c.z),
                                         (math.cos(a) * 0.5, math.sin(a) * 0.5, sun_c.z + 0.08)], (math.cos(a) * 1.05, math.sin(a) * 1.05, sun_c.z)), metal(GOLD)))
    # statues of past emperors in the garden corners
    looks = [dict(C.CAST["emperor"], prop="staff"), dict(C.CAST["thane"], headwear="laurel_gold"), dict(C.CAST["empress"]), dict(C.CAST["marcellan"], headwear="laurel_gold")]
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        P += statue(looks[i], sx * 9.3, sy * 9.3, math.atan2(sx, -sy) + math.pi, 1.7)
    for (x, y) in ((-12.4, -4.6), (-4.6, -12.4), (12.4, -4.6), (4.6, -12.4), (-12.4, 4.6), (-4.6, 12.4), (12.4, 4.6), (4.6, 12.4)):
        P += cypress(x, y, 6.5, 0.3)
    # the colonnade and its tiled roofs
    for t in (-14.0, -10.0, -6.0, -2.0, 2.0, 6.0, 10.0, 14.0):
        P += column(t, -COL)
        P += column(t, COL)
        if abs(t) < 13.9:
            P += column(-COL, t)
            P += column(COL, t)
    for (a, b) in (((-COL, -COL), (COL, -COL)), ((COL, -COL), (COL, COL)), ((COL, COL), (-COL, COL)), ((-COL, COL), (-COL, -COL))):
        P += entablature(a, b, COL_H)
    zr = COL_H + 1.2
    P += lean_roof((-COL - 0.6, -COL - 0.6), (COL + 0.6, -COL - 0.6), (0, -1, 0), H - COL - 0.3, zr, 1.1)
    P += lean_roof((COL + 0.6, COL + 0.6), (-COL - 0.6, COL + 0.6), (0, 1, 0), H - COL - 0.3, zr, 1.1)
    P += lean_roof((-COL - 0.6, COL + 0.6), (-COL - 0.6, -COL - 0.6), (-1, 0, 0), H - COL - 0.3, zr, 1.1)
    P += lean_roof((COL + 0.6, -COL - 0.6), (COL + 0.6, COL + 0.6), (1, 0, 0), H - COL - 0.3, zr, 1.1)
    # walls with the four great doorways (the north one stands open onto the Council Chamber)
    P += wall((-H, -H), (H, -H), WALL_H, [(H, 3.4)])
    P += wall((H, H), (-H, H), WALL_H, [(H, 3.4)])
    P += wall((-H, H), (-H, -H), WALL_H, [(H, 3.4)])
    P += wall((H, -H), (H, H), WALL_H, [(H, 3.4)])
    # banners between the doors, braziers by the doors, urns at the corners
    for t in (-9.0, 9.0):
        P += banner(t, -H + 0.45, 0.0, 6.6)
        P += banner(t, H - 0.45, math.pi, 6.6)
        P += banner(-H + 0.45, t, -math.pi / 2, 6.6)
        P += banner(H - 0.45, t, math.pi / 2, 6.6)
    for (x, y) in ((-3.6, -16.4), (3.6, -16.4), (-3.6, 16.4), (3.6, 16.4), (16.4, -3.6), (16.4, 3.6), (-16.4, -3.6), (-16.4, 3.6)):
        P += brazier(x, y, 0.0, 1.0, light=(y < 0))
    for (x, y) in ((-16.6, -16.6), (16.6, -16.6), (-16.6, 16.6), (16.6, 16.6)):
        P += urn(x, y)
    for (x, y, rot) in ((-16.9, 10.0, math.pi / 2), (16.9, -10.0, math.pi / 2), (-10.0, -16.9, 0.0), (10.0, 16.9, 0.0)):
        P.append(done(block("Bench", (x, y, 0.42), (3.0, 0.7, 0.14), (0, 0, rot)), col_(MARBLE)))
        for k in (-1, 1):
            off = Vector((k * 1.2, 0, 0))
            off.rotate(Euler((0, 0, rot)))
            P.append(done(block("BenchLeg", (x + off.x, y + off.y, 0.2), (0.4, 0.6, 0.4), (0, 0, rot)), col_(MARBLE2)))
    # the wings beyond: tiled roofs, and the gilded dome of the Council Chamber
    P += hip_roof(0, -32, 30, 28, WALL_H + 0.8, 5.5)
    P += dome(0, -32, WALL_H + 3.5, 8.0)
    P += hip_roof(38, 0, 40, 26, WALL_H + 0.8, 6.0)
    P += hip_roof(-36, 0, 36, 26, WALL_H + 1.5, 6.5)
    P += hip_roof(0, 36, 28, 26, WALL_H, 5.0)
    for (x, y, w, d, h) in ((0, -32, 30, 28, WALL_H + 0.8), (38, 0, 40, 26, WALL_H + 0.8), (-36, 0, 36, 26, WALL_H + 1.5), (0, 36, 28, 26, WALL_H)):
        P.append(done(block("WingWall", (x, y, h / 2), (w - 0.4, d - 0.4, h)), col_(PLASTER)))
        P.append(done(block("WingBand", (x, y, h - 0.6), (w - 0.2, d - 0.2, 0.7)), col_(OCHRE)))
    P.append(done(block("Ground", (0, 0, -0.06), (160, 160, 0.1)), col_("cdbb9a")))
    return P


def people():
    """A few members of the court in the courtyard, for scale and life."""
    groups = [("emperor", (2.5, -5.2), 2.6), ("chancellor", (3.6, -6.4), 0.4), ("thrask", (-6.6, -7.8), -1.9), ("korrach", (-5.2, -8.6), 1.2),
              ("ilsaveth", (-9.2, 6.8), 2.4), ("empress", (-8.2, 7.6), -1.0), ("cassia", (-2.4, -16.6), 0.0), ("thane", (2.4, -16.6), 0.0),
              ("player", (3.2, 9.2), math.pi - 0.3), ("aldric", (4.4, 10.2), math.pi - 0.6), ("oduvar", (10.5, -2.4), 0.9), ("ulda", (11.4, -1.4), 2.6)]
    for cid, (x, y), yaw in groups:
        parts = C.Figure(cid, C.CAST[cid]).build()
        place(parts, (x, y, 0.21 if abs(x) < 6 and abs(y) < 6 else 0.0), yaw)


def lighting(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
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
    cr.elements[0].color = K.hexc("f2a464")
    cr.elements[1].position = 0.5
    cr.elements[1].color = K.hexc("2e2766")
    cr.elements.new(0.07).color = K.hexc("f7c58e")
    cr.elements.new(0.2).color = K.hexc("b885ae")
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.55
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 30))
    sun = bpy.context.active_object
    sun.data.energy = 3.6
    sun.data.color = (1.0, 0.7, 0.45)
    sun.data.angle = math.radians(2.0)
    sun.rotation_euler = Euler((math.radians(68), 0, math.radians(-115)))


def shoot(path, loc, target, lens=28, res=(1600, 900)):
    K.shoot(path, loc, target, lens, res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--no-people", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = build_peristyle()
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
    print("peristyle objects:", len(parts), "triangles:", tris)
    os.makedirs(os.path.join(ROOT, "assets", "palace"), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "assets", "palace", "peristyle.glb"), use_selection=True, export_format="GLB")
    if not args.no_people:
        people()
    lighting(args.samples)
    out = os.path.join(ROOT, "renders")
    shots = {
        "palace_courtyard": ((0.0, 12.8, 1.75), (0.0, -8.0, 3.2), 24),
        "palace_fountain": ((-4.2, 3.6, 1.8), (3.0, -6.0, 1.9), 30),
        "palace_overview": ((34.0, 40.0, 30.0), (0.0, -4.0, 0.0), 30),
        "palace_colonnade": ((16.2, 12.0, 1.7), (15.4, -14.0, 3.0), 24),
    }
    for k, (loc, tgt, lens) in shots.items():
        if args.only and k not in args.only.split(","):
            continue
        shoot(os.path.join(out, k + ".png"), loc, tgt, lens)


if __name__ == "__main__":
    main()
