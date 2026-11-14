"""Kharad head, hand-placed low-poly (every vertex chosen, every facet deliberate).

Run:  python3 imperium/blender/kharad_head.py [--samples N]
Writes imperium/renders/kharad_head_sheet.png (four studies) and assets/characters/kharad_head.glb.

Construction: the skull/snout is a series of hand-drawn cross-section slices (front to back) joined
into crisp planes; the jaw is a separate hinged piece; brows, eyes, horns, spikes and crown are
small explicit meshes. Flat colours only: the light does the shading, as in hand-made low-poly kits.
Axes: Z up, the head faces -Y, +X is the character's left. Z0 lifts the head to standing height.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

import kharad as K  # noqa: E402  (palette, materials, stage, cameras)

ROOT = K.ROOT
Z0 = 2.0

# ----------------------------------------------------------------------------- hand-drawn shapes
# Upper head: slices front -> back. Each is (y, half-profile) with the half-profile running from the
# top centre line, down the character's left side, to the bottom centre line: [(x, z), ...].
UPPER_RAW = [
    (-0.43, [(0.0, 0.03), (0.022, 0.028), (0.03, 0.006), (0.024, -0.012), (0.0, -0.014)]),
    (-0.37, [(0.0, 0.055), (0.04, 0.05), (0.056, 0.018), (0.05, -0.014), (0.0, -0.018)]),
    (-0.27, [(0.0, 0.078), (0.052, 0.074), (0.077, 0.032), (0.072, -0.016), (0.0, -0.022)]),
    (-0.18, [(0.0, 0.1), (0.07, 0.118), (0.1, 0.062), (0.094, -0.012), (0.0, -0.024)]),   # brow rises
    (-0.08, [(0.0, 0.142), (0.066, 0.134), (0.116, 0.078), (0.118, 0.0), (0.0, -0.026)]),
    (0.02, [(0.0, 0.13), (0.058, 0.118), (0.1, 0.064), (0.1, -0.012), (0.0, -0.034)]),
    (0.075, [(0.0, 0.082), (0.04, 0.074), (0.064, 0.04), (0.06, 0.0), (0.0, -0.02)]),
]
# a broader, taller skull than the snout: scale the back slices up
def _sx(y):
    """Width scale: a broad skull tapering into a still-sturdy snout."""
    t = min(1.0, max(0.0, (y + 0.32) / 0.22))
    t = t * t * (3 - 2 * t)
    return 1.3 + 0.32 * t


SZ = 1.2
UPPER = [(y, [(x * _sx(y), z * SZ) for (x, z) in half]) for (y, half) in UPPER_RAW]


def surface_x(y, z):
    """Half-width of the skull at (y, z): interpolate the slices, then walk the side of the profile."""
    for (y0, h0), (y1, h1) in zip(UPPER, UPPER[1:]):
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            half = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(h0, h1)]
            break
    else:
        return 0.0
    best = 0.0
    for (xa, za), (xb, zb) in zip(half, half[1:]):
        lo, hi = min(za, zb), max(za, zb)
        if lo <= z <= hi and hi > lo:
            best = max(best, xa + (xb - xa) * (z - za) / (zb - za))
    return best


def top_z(y):
    for (y0, h0), (y1, h1) in zip(UPPER, UPPER[1:]):
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return max(a[1] + (b[1] - a[1]) * t for a, b in zip(h0, h1))
    return 0.0
# Lower jaw: (y, half-width, top z, bottom z). Slightly narrower than the upper head; hinged at the back.
JAW = [
    (-0.4, 0.03, -0.03, -0.05),
    (-0.33, 0.058, -0.034, -0.07),
    (-0.22, 0.088, -0.036, -0.09),
    (-0.1, 0.122, -0.04, -0.112),
    (0.0, 0.132, -0.046, -0.12),
    (0.05, 0.1, -0.036, -0.09),
]


def mirror_ring(half):
    """Half-profile (top centre -> left -> bottom centre) to a full ring: top, left side, bottom, right side."""
    left = [Vector((x, 0, z)) for (x, z) in half]
    right = [Vector((-x, 0, z)) for (x, z) in half[1:-1]]
    return left + list(reversed(right))


def slices_mesh(name, slices, ring_fn):
    bm = bmesh.new()
    rings = []
    for y, data in slices:
        pts = ring_fn(data)
        rings.append([bm.verts.new((p.x, y, p.z + Z0)) for p in pts])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4 and not _planar(f)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K.new_obj(name, me)


def _planar(f, tol=0.0015):
    n = f.normal
    p0 = f.verts[0].co
    return all(abs((v.co - p0).dot(n)) < tol for v in f.verts)


def jaw_ring(d):
    w, top, bot = d
    return [Vector((0, 0, top)), Vector((w, 0, top)), Vector((w * 0.86, 0, bot)), Vector((0, 0, bot - 0.008)),
            Vector((-w * 0.86, 0, bot)), Vector((-w, 0, top))]


def explicit(name, verts, faces, mirror=True):
    """A small mesh from explicit (x, y, z) vertices and faces, optionally mirrored across X."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z + Z0)) for (x, y, z) in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    if mirror:
        ms = [bm.verts.new((-x, y, z + Z0)) for (x, y, z) in verts]
        for f in faces:
            bm.faces.new([ms[i] for i in reversed(f)])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K.new_obj(name, me)


def angular_tube(name, path, radii, sides=4, twist=0.0):
    """A tapering tube with few sides along a hand-placed path (horns): crisp, planar flanks."""
    bm = bmesh.new()
    rings = []
    pts = [Vector(p) for p in path]
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(t).normalized()
        r = radii[k]
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides + twist * k + math.pi / sides
            ring.append(bm.verts.new(p + (side * math.cos(a) + up * math.sin(a)) * r + Vector((0, 0, Z0))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    if radii[-1] > 0.0005:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K.new_obj(name, me)


def flat(obj, material, region=None, materials=None):
    """Flat shading, no colour noise. `region(center, normal) -> material index` picks per-face colours."""
    obj.data.materials.clear()
    for m in ([material] + (materials or [])):
        obj.data.materials.append(m)
    for p in obj.data.polygons:
        p.use_smooth = False
        if region:
            p.material_index = region(p.center, p.normal)
    return K.finish(obj, material, 0.0) if not materials else _keep(obj)


def _keep(obj):
    me = obj.data
    if "facet" not in me.color_attributes:
        ca = me.color_attributes.new("facet", "BYTE_COLOR", "CORNER")
        for d in ca.data:
            d.color = (1, 1, 1, 1)
    return obj


# ----------------------------------------------------------------------------- the head
def build_head():
    skin = K.mat("HSkin", K.SKIN, rough=0.85)
    belly = K.mat("HBelly", "7f8650", rough=0.85)
    dark = K.mat("HDark", K.SKIN_DARK, rough=0.85)
    bone = K.mat("HBone", K.BONE, rough=0.6)
    inner = K.mat("HMouth", "3a1a1c", rough=0.9)
    black = K.mat("HBlack", "141012", rough=0.4)
    eye = K.mat("HEye", "ffc23a", rough=0.3, emit="ffae00", emit_strength=6.0)
    iron = K.mat("HIron", K.IRON, rough=0.55, metal=0.3)
    gem = K.mat("HGem", "b31d2a", rough=0.15, emit="5a0a10", emit_strength=0.8)
    gold = K.mat("HGold", K.GOLD, rough=0.5, metal=0.3)
    char = K.mat("HChar", K.CHARCOAL, rough=0.9)
    parts = []

    # skull and snout: top planes skin, under-plane pale, brow top darker
    up = slices_mesh("Skull", UPPER, mirror_ring)
    parts.append(flat(up, skin, lambda c, n: 1 if n.z < -0.55 else (2 if (n.z > 0.75 and -0.24 < c.y < -0.04) else 0), [belly, dark]))
    jaw = slices_mesh("Jaw", [(y, (w, t, b)) for (y, w, t, b) in JAW], jaw_ring)
    parts.append(flat(jaw, skin, lambda c, n: 1 if n.z < -0.3 else 0, [belly]))
    # the dark mouth between them
    parts.append(flat(explicit("Mouth", [(0.0, -0.41, -0.022), (0.028, -0.4, -0.024), (0.09, -0.25, -0.028), (0.122, -0.08, -0.034), (0.0, -0.08, -0.034)],
                               [(0, 1, 2, 4), (2, 3, 4)]), inner))

    # eye: a narrow glowing diamond set into the side plane, a slit pupil, a brow blade above
    ey, ez = -0.15, 0.085
    sxe = surface_x(ey, ez)
    nrm = 0.006
    eye_v = [(surface_x(-0.195, 0.08) + nrm * 0.5, -0.195, 0.08), (surface_x(ey, 0.104) + nrm, ey, 0.104),
             (surface_x(-0.1, 0.092) + nrm * 0.5, -0.1, 0.092), (surface_x(ey, 0.068) + nrm, ey, 0.068), (sxe + nrm * 1.6, ey, 0.086)]
    parts.append(flat(explicit("Eye", eye_v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]), eye))
    parts.append(flat(explicit("Pupil", [(sxe + nrm * 1.9, ey - 0.006, 0.1), (sxe + nrm * 1.9, ey + 0.006, 0.1), (sxe + nrm * 1.9, ey + 0.006, 0.072), (sxe + nrm * 1.9, ey - 0.006, 0.072)],
                               [(0, 1, 2, 3)]), black))
    bz = 0.122
    brow = [(surface_x(-0.235, 0.105) * 0.7, -0.235, top_z(-0.235) + 0.004), (surface_x(-0.17, bz) + 0.022, -0.17, bz + 0.012),
            (surface_x(-0.04, bz) + 0.03, -0.04, bz + 0.03), (surface_x(-0.1, 0.14) * 0.75, -0.1, top_z(-0.1) + 0.008),
            (surface_x(-0.17, 0.1) + 0.006, -0.16, 0.103)]
    parts.append(flat(explicit("Brow", brow, [(0, 1, 3), (1, 2, 3), (0, 4, 1), (4, 2, 1), (0, 3, 4)]), dark))
    # nostrils: two small dark slashes on the snout top
    nz = top_z(-0.39) + 0.002
    parts.append(flat(explicit("Nostril", [(0.016, -0.405, nz - 0.004), (0.036, -0.39, nz - 0.003), (0.038, -0.375, nz), (0.02, -0.392, nz)], [(0, 1, 2, 3)]), black))
    # cheek spikes and a fan of frills behind the jaw
    spk_v, spk_f = [], []
    for (root, tip, w) in (((surface_x(-0.04, 0.02) - 0.01, -0.04, 0.02), (surface_x(-0.04, 0.02) + 0.08, 0.07, 0.03), 0.024),
                           ((0.125, 0.0, -0.07), (0.2, 0.1, -0.1), 0.02),
                           ((0.1, 0.04, -0.1), (0.15, 0.13, -0.16), 0.016)):
        b = len(spk_v)
        r = Vector(root)
        spk_v += [tuple(r + Vector((0, -w, w))), tuple(r + Vector((0, w, w))), tuple(r + Vector((0, 0, -w))), tip]
        spk_f += [(b, b + 1, b + 3), (b + 1, b + 2, b + 3), (b + 2, b, b + 3), (b, b + 2, b + 1)]
    parts.append(flat(explicit("Spikes", spk_v, spk_f), dark))

    # horns: square-section, twisting slightly, sweeping back and up
    for sx in (1, -1):
        for (base, s) in (((0.085, 0.045, 0.13), 1.0), ((0.12, 0.05, 0.06), 0.72)):
            bx, by, bz = base
            path = [(sx * bx, by, bz), (sx * (bx + 0.03 * s), by + 0.12 * s, bz + 0.05 * s), (sx * (bx + 0.05 * s), by + 0.24 * s, bz + 0.12 * s),
                    (sx * (bx + 0.06 * s), by + 0.32 * s, bz + 0.22 * s), (sx * (bx + 0.055 * s), by + 0.33 * s, bz + 0.31 * s)]
            h = angular_tube("Horn", path, [0.05 * s, 0.042 * s, 0.03 * s, 0.016 * s, 0.0], 4, 0.18 * sx)
            parts.append(flat(h, bone, lambda c, n: 1 if c.z < Z0 + 0.2 else 0, [K.mat("HBoneDark", "b9a690", rough=0.6)]))

    # crown: a seven-sided iron band with triangular spikes and a cut garnet at the front
    sides = 7
    cv, cf = [], []
    zb = 0.138
    ys = [y / 100.0 for y in range(-30, 8)]
    inside = [y for y in ys if top_z(y) >= zb]
    cy0 = (inside[0] + inside[-1]) / 2
    ry = (inside[-1] - inside[0]) / 2 + 0.012
    rx = max(surface_x(y, zb) for y in inside) + 0.012
    for i in range(sides):
        a = -math.pi / 2 + 2 * math.pi * i / sides
        x, y = math.cos(a) * rx, cy0 + math.sin(a) * ry
        cv += [(x, y, zb), (x * 1.04, cy0 + (y - cy0) * 1.04, zb + 0.05)]
    for i in range(sides):
        j = (i + 1) % sides
        cf.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    for i in range(sides):
        a = -math.pi / 2 + 2 * math.pi * i / sides
        a2 = a + math.pi / sides
        h = 0.1 if i == 0 else 0.06
        b = len(cv)
        mx, my = math.cos(a) * rx * 1.04, cy0 + math.sin(a) * ry * 1.04
        nx, ny = math.cos(a2) * rx * 1.04, cy0 + math.sin(a2) * ry * 1.04
        px, py = math.cos(a - math.pi / sides) * rx * 1.04, cy0 + math.sin(a - math.pi / sides) * ry * 1.04
        cv += [(px, py, zb + 0.05), (nx, ny, zb + 0.05), (mx * 1.06, cy0 + (my - cy0) * 1.06, zb + 0.05 + h), (mx * 0.9, cy0 + (my - cy0) * 0.9, zb + 0.05)]
        cf += [(b, b + 1, b + 2), (b + 1, b + 3, b + 2), (b + 3, b, b + 2)]
    crown = explicit("Crown", cv, cf, mirror=False)
    parts.append(flat(crown, iron))
    g = 0.0
    gy = cy0 - ry * 1.02 - 0.004
    parts.append(flat(explicit("Garnet", [(0, gy - 0.014, zb + 0.025), (0.017, gy, zb + 0.025), (0, gy, zb + 0.052), (0, gy, zb - 0.002)],
                               [(0, 1, 2), (0, 3, 1)]), gem))

    # neck and a collar, so the head studies read as a bust
    neck = K.loft("Neck", [(Z0 - 0.36, 0.17, 0.15, 0, 0.0), (Z0 - 0.2, 0.135, 0.12, 0, -0.015), (Z0 - 0.02, 0.12, 0.11, 0, 0.0)], seg=8)
    parts.append(flat(neck, skin, lambda c, n: 1 if n.y < -0.6 else 0, [belly]))
    col_v = []
    cf2 = []
    for i in range(8):
        a = 2 * math.pi * i / 8
        col_v += [(math.cos(a) * 0.19, math.sin(a) * 0.17, -0.33), (math.cos(a) * 0.36, math.sin(a) * 0.28, -0.44)]
    for i in range(8):
        j = (i + 1) % 8
        cf2.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    parts.append(flat(explicit("Collar", col_v, cf2, mirror=False), char))
    rim_v = []
    for i in range(8):
        a = 2 * math.pi * i / 8
        rim_v += [(math.cos(a) * 0.19, math.sin(a) * 0.17, -0.325), (math.cos(a) * 0.215, math.sin(a) * 0.19, -0.35)]
    parts.append(flat(explicit("CollarRim", rim_v, cf2, mirror=False), gold))
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--out", default=os.path.join(ROOT, "renders"))
    args = ap.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = build_head()
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
    print("head parts:", len(parts), "triangles:", tris)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    os.makedirs(os.path.join(ROOT, "assets", "characters"), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "assets", "characters", "kharad_head.glb"), use_selection=True, export_format="GLB")
    K.stage(args.samples)
    os.makedirs(args.out, exist_ok=True)
    tgt = (0, -0.12, Z0 + 0.02)
    shots = {"a": (-38, 10, 1.25), "b": (-90, 4, 1.3), "c": (0, 8, 1.25), "d": (-140, 22, 1.35)}
    files = {}
    for k, (yaw, pitch, dist) in shots.items():
        files[k] = os.path.join(args.out, "kharad_head_%s.png" % k)
        K.shoot(files[k], K.orbit(tgt, dist, yaw, pitch), (0, -0.08 if k != "d" else 0.0, Z0 + 0.02), 60, (800, 800))
    sheet(os.path.join(args.out, "kharad_head_sheet.png"), files)


def sheet(out, files):
    from PIL import Image, ImageDraw
    W, H = 1400, 1400
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(148 - 36 * t), int(94 - 26 * t), int(78 - 20 * t)))
    d.line([(W // 2, 0), (W // 2, H)], fill=(118, 74, 60), width=3)
    d.line([(0, H // 2), (W, H // 2)], fill=(118, 74, 60), width=3)
    for idx, k in enumerate(("a", "b", "c", "d")):
        im = Image.open(files[k]).convert("RGBA")
        bb = im.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
        if bb:
            im = im.crop((max(0, bb[0] - 30), max(0, bb[1] - 30), min(im.width, bb[2] + 30), min(im.height, bb[3] + 30)))
        s = min(660 / im.width, 660 / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        ox, oy = (idx % 2) * (W // 2), (idx // 2) * (H // 2)
        bg.paste(im, (ox + (W // 2 - im.width) // 2, oy + (H // 2 - im.height) // 2), im)
    bg.save(out)
    print("sheet", out)


if __name__ == "__main__":
    main()
