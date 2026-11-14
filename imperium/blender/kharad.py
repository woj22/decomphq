"""Kharad warrior-king (Thrask of Khar-Dumeth), modelled procedurally in Blender.

Run:  python3 imperium/blender/kharad.py [--samples N] [--no-render]
Writes a character sheet (full body, four head views, palette) to imperium/renders/kharad_sheet.png,
the individual renders next to it, and the model to imperium/assets/characters/kharad_thrask.glb.

Style: big flat facets, a muted palette (olive, charcoal, gold, crimson, bone) and warm studio light.
Blender axes: Z up, the character faces -Y, +X is the character's left.
"""
import argparse
import math
import os
import random

import bpy  # must come first: it provides bmesh and mathutils
import bmesh
from mathutils import Euler, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = random.Random(11)

# ----------------------------------------------------------------------------- palette (the sheet's swatches)
SKIN = "5b6235"
SKIN_DARK = "40452a"
SKIN_LIGHT = "7f8248"
CHARCOAL = "38333a"
GOLD = "c8862d"
CRIMSON = "7f1d24"
BONE = "e2d3c3"
LEATHER = "5b3a28"
IRON = "2b282c"
EYE = "ffc23a"
SWATCHES = [SKIN_DARK, SKIN_LIGHT, CHARCOAL, GOLD, CRIMSON, BONE]


def hexc(h, a=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


# ----------------------------------------------------------------------------- helpers
def mat(name, color, rough=0.8, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "facet"
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    mul.inputs[6].default_value = hexc(color)
    nt.links.new(attr.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
    if emit:
        bsdf.inputs["Emission Color"].default_value = hexc(emit)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


def finish(obj, material, jitter=0.035, region_fn=None):
    """Flat shading + a per-face colour attribute (facet variation, optional regional tint)."""
    obj.data.materials.clear()
    obj.data.materials.append(material)
    me = obj.data
    for p in me.polygons:
        p.use_smooth = False
    if "facet" not in me.color_attributes:
        me.color_attributes.new("facet", "BYTE_COLOR", "CORNER")
    ca = me.color_attributes["facet"]
    for p in me.polygons:
        f = 1.0 + rng.uniform(-jitter, jitter)
        tint = (1.0, 1.0, 1.0)
        if region_fn:
            tint = region_fn(obj.matrix_world @ p.center, obj.matrix_world.to_3x3() @ p.normal)
        col = (min(1, tint[0] * f), min(1, tint[1] * f), min(1, tint[2] * f), 1.0)
        for li in p.loop_indices:
            ca.data[li].color = col
    return obj


def apply_all(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def new_obj(name, me):
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    return obj


SKIN_K = 1.12   # skin radii are box half-sizes; subdivision shrinks them a little


def skin_object(name, nodes, edges, root=0, subsurf=1, decimate=0.3):
    """Organic form from a node graph: nodes [(x, y, z, rx[, ry])], edges [(i, j)]."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([n[:3] for n in nodes], edges, [])
    obj = new_obj(name, me)
    mod = obj.modifiers.new("skin", "SKIN")
    mod.branch_smoothing = 0.5
    sv = me.skin_vertices[0].data
    for i, n in enumerate(nodes):
        rx = n[3] * SKIN_K
        ry = (n[4] if len(n) > 4 else n[3]) * SKIN_K
        sv[i].radius = (rx, ry)
        sv[i].use_root = i == root
    if subsurf:
        s = obj.modifiers.new("sub", "SUBSURF")
        s.levels = subsurf
    if decimate < 1.0:
        d = obj.modifiers.new("dec", "DECIMATE")
        d.ratio = decimate
    apply_all(obj)
    return obj


def loft(name, rings, arc=None, cap_top=False, cap_bottom=False, solidify=0.0, seg=16, decimate=1.0):
    """rings: [(z, rx, ry, cx, cy[, wobble])], lofted bottom-up into a tube, or an open shell for arc=(a0, a1).
    Angles are measured from +X toward +Y (the character's back is +Y, the front -Y)."""
    bm = bmesh.new()
    vr = []
    for ring in rings:
        z, rx, ry, cx, cy = ring[:5]
        wob = ring[5] if len(ring) > 5 else 0.0
        n = seg if arc is None else seg + 1
        row = []
        for i in range(n):
            t = (2 * math.pi * i / seg) if arc is None else arc[0] + (arc[1] - arc[0]) * i / seg
            f = 1.0 + (wob if i % 2 == 0 else -wob)
            row.append(bm.verts.new((cx + math.cos(t) * rx * f, cy + math.sin(t) * ry * f, z)))
        vr.append(row)
    for a, b in zip(vr, vr[1:]):
        n = len(a)
        for i in (range(n) if arc is None else range(n - 1)):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_top and arc is None:
        bm.faces.new(vr[-1])
    if cap_bottom and arc is None:
        bm.faces.new(list(reversed(vr[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = new_obj(name, me)
    if solidify:
        s = obj.modifiers.new("sol", "SOLIDIFY")
        s.thickness = solidify
        s.offset = 0
    if decimate < 1.0:
        d = obj.modifiers.new("dec", "DECIMATE")
        d.ratio = decimate
    apply_all(obj)
    return obj


def loft_y(name, rings, seg=8, decimate=1.0):
    """Loft along -Y (heads, snouts): rings [(y, rx, rz, cz)], capped at both ends."""
    bm = bmesh.new()
    vr = []
    for (y, rx, rz, cz) in rings:
        row = []
        for i in range(seg):
            t = 2 * math.pi * i / seg + math.pi / seg
            row.append(bm.verts.new((math.cos(t) * rx, y, cz + math.sin(t) * rz)))
        vr.append(row)
    for a, b in zip(vr, vr[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(vr[0])
    bm.faces.new(list(reversed(vr[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = new_obj(name, me)
    if decimate < 1.0:
        d = o.modifiers.new("dec", "DECIMATE")
        d.ratio = decimate
        apply_all(o)
    return o


def prim(kind, name, loc, scale=(1, 1, 1), rot=(0, 0, 0), **kw):
    ops = {"cone": bpy.ops.mesh.primitive_cone_add, "ico": bpy.ops.mesh.primitive_ico_sphere_add,
           "cyl": bpy.ops.mesh.primitive_cylinder_add, "cube": bpy.ops.mesh.primitive_cube_add,
           "sphere": bpy.ops.mesh.primitive_uv_sphere_add}
    ops[kind](location=loc, rotation=rot, **kw)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o


def _aim(o, a, b):
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (b - a).to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)


def wedge(name, a, b, width, depth, material, jitter=0.03):
    """A flat, tapering plate from point a to point b (brows)."""
    a, b = Vector(a), Vector(b)
    o = prim("cone", name, (a + b) / 2, (width, depth, (b - a).length / 2), vertices=4)
    _aim(o, a, b)
    return finish(o, material, jitter)


def spike(name, base, tip, r, material, verts=4):
    base, tip = Vector(base), Vector(tip)
    o = prim("cone", name, (base + tip) / 2, (r, r, (tip - base).length / 2), vertices=verts)
    _aim(o, base, tip)
    return finish(o, material, 0.03)


# ----------------------------------------------------------------------------- the body
def build_body():
    nodes = [
        (0, 0.02, 1.12, 0.165, 0.15),   # 0 pelvis (root)
        (0, 0.0, 1.32, 0.145, 0.125),   # 1 waist
        (0, -0.03, 1.56, 0.25, 0.19),   # 2 chest
        (0, 0.0, 1.76, 0.24, 0.17),     # 3 upper chest / shoulders
        (0, -0.02, 1.9, 0.095),         # 4 neck
        (0, -0.05, 2.02, 0.08),         # 5 upper neck
        (0, -0.04, 2.1, 0.06),          # 6 (into the head)
        (0, 0.17, 1.06, 0.12),          # 7 tail
        (0, 0.42, 0.82, 0.09),          # 8
        (0, 0.66, 0.52, 0.065),         # 9
        (0, 0.86, 0.26, 0.04),          # 10
        (0, 1.0, 0.09, 0.012),          # 11
    ]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (0, 7), (7, 8), (8, 9), (9, 10), (10, 11)]
    side = [
        (0.2, 0.0, 1.79, 0.11),      # 0 clavicle
        (0.37, 0.02, 1.75, 0.14),    # 1 shoulder
        (0.46, 0.07, 1.43, 0.1),     # 2 elbow
        (0.5, -0.01, 1.14, 0.08),    # 3 wrist
        (0.51, -0.04, 1.02, 0.1, 0.085),  # 4 fist
        (0.15, 0.02, 1.1, 0.15),     # 5 hip
        (0.17, -0.13, 0.72, 0.1),    # 6 knee (forward)
        (0.18, 0.1, 0.33, 0.07),     # 7 hock (raised heel: digitigrade)
        (0.19, -0.07, 0.07, 0.06),   # 8 ball of the foot
        (0.25, -0.3, 0.035, 0.028),  # 9 toe outer
        (0.19, -0.34, 0.035, 0.03),  # 10 toe middle
        (0.13, -0.3, 0.035, 0.028),  # 11 toe inner
    ]
    side_edges = [("chest", 0), (0, 1), (1, 2), (2, 3), (3, 4),
                  ("pelvis", 5), (5, 6), (6, 7), (7, 8), (8, 9), (8, 10), (8, 11)]
    for sign in (1, -1):
        base = len(nodes)
        for n in side:
            nodes.append((n[0] * sign, *n[1:]))
        for a, b in side_edges:
            ia = 3 if a == "chest" else 0 if a == "pelvis" else base + a
            edges.append((ia, base + b))
    body = skin_object("KharadBody", nodes, edges, root=0, subsurf=1, decimate=0.32)

    def region(p, n):
        if n.y > 0.4 and p.z > 0.3:
            return (0.78, 0.8, 0.76)          # darker back
        if n.y < -0.35 and abs(p.x) < 0.16 and 1.0 < p.z < 2.1:
            return (1.35, 1.3, 1.18)          # paler throat and belly
        if n.z > 0.6:
            return (1.12, 1.1, 1.05)
        return (1.0, 1.0, 1.0)
    finish(body, mat("KharadSkin", SKIN), 0.06, region)
    parts = [body]
    claw = mat("Claw", BONE, rough=0.5)
    for sx in (1, -1):
        for (x, y) in ((0.25, -0.3), (0.19, -0.34), (0.13, -0.3)):
            parts.append(spike("claw", (sx * x, y - 0.03, 0.035), (sx * x, y - 0.12, 0.0), 0.022, claw))
        parts.append(spike("heelspur", (sx * 0.18, 0.12, 0.3), (sx * 0.18, 0.22, 0.26), 0.022, mat("KharadSkinDark", SKIN_DARK)))
        for k in range(3):
            parts.append(spike("knuckle", (sx * (0.49 + k * 0.025), -0.1, 1.05), (sx * (0.49 + k * 0.025), -0.15, 1.03), 0.014, claw))
    return parts


# ----------------------------------------------------------------------------- the head
HEAD = [  # (y, rx, rz, cz): back of the skull to the tip of the snout (a long, flat-topped wedge)
    (0.05, 0.05, 0.06, 2.15),
    (0.0, 0.1, 0.095, 2.155),
    (-0.08, 0.105, 0.088, 2.16),
    (-0.17, 0.08, 0.066, 2.145),
    (-0.26, 0.063, 0.05, 2.125),
    (-0.33, 0.045, 0.036, 2.112),
    (-0.365, 0.02, 0.02, 2.105),
]
JAW = [(-0.0, 0.08, 0.04, 2.08), (-0.13, 0.072, 0.036, 2.075), (-0.26, 0.05, 0.026, 2.075), (-0.33, 0.026, 0.018, 2.08)]


def head_at(y):
    for a, b in zip(HEAD, HEAD[1:]):
        if a[0] >= y >= b[0]:
            t = (a[0] - y) / (a[0] - b[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in (1, 2, 3))
    return HEAD[-1][1:]


def build_head():
    skin = mat("KharadSkin", SKIN)
    dark = mat("KharadSkinDark", SKIN_DARK)
    bone = mat("Bone", BONE, rough=0.55)
    black = mat("Black", "15110f")
    parts = []

    def hr(p, n):
        if n.z < -0.4:
            return (1.3, 1.26, 1.15)
        if n.z > 0.6:
            return (0.88, 0.9, 0.85)
        return (1, 1, 1)
    parts.append(finish(loft_y("Head", HEAD), skin, 0.05, hr))
    parts.append(finish(loft_y("Jaw", JAW), skin, 0.05, lambda p, n: (1.3, 1.26, 1.15) if n.z < 0 else (1, 1, 1)))
    eye_m = mat("KharadEye", EYE, rough=0.2, emit="ffb000", emit_strength=8.0)
    for sx in (1, -1):
        rx, rz, cz = head_at(-0.16)
        parts.append(wedge("brow", (sx * rx * 0.55, -0.24, cz + rz * 0.62), (sx * rx * 1.05, -0.07, cz + rz * 1.02), 0.035, 0.012, dark))
        e = prim("ico", "eye", (sx * rx * 0.9, -0.165, cz + rz * 0.42), (0.018, 0.046, 0.014), (0.25, 0.0, sx * 0.3), subdivisions=1, radius=1)
        parts.append(finish(e, eye_m, 0.0))
        parts.append(spike("cheek", (sx * 0.08, -0.03, 2.1), (sx * 0.15, 0.09, 2.1), 0.022, dark))
        parts.append(spike("jawspike", (sx * 0.065, 0.0, 2.06), (sx * 0.12, 0.1, 2.02), 0.018, dark))
        parts.append(spike("crest", (sx * 0.05, 0.03, 2.2), (sx * 0.07, 0.13, 2.25), 0.016, dark))
        parts.append(finish(prim("cube", "lip", (sx * 0.045, -0.2, 2.087), (0.004, 0.11, 0.004), (0, 0, sx * -0.12)), black, 0.0))
        parts.append(finish(prim("cube", "nostril", (sx * 0.022, -0.345, 2.135), (0.008, 0.012, 0.005)), black, 0.0))
        for (bx, by, bz, s) in ((0.07, 0.0, 2.21, 1.0), (0.095, 0.03, 2.15, 0.7)):
            hn = [(sx * bx, by, bz, 0.034 * s),
                  (sx * (bx + 0.03 * s), by + 0.16 * s, bz + 0.07 * s, 0.03 * s),
                  (sx * (bx + 0.05 * s), by + 0.32 * s, bz + 0.15 * s, 0.021 * s),
                  (sx * (bx + 0.06 * s), by + 0.44 * s, bz + 0.27 * s, 0.011 * s),
                  (sx * (bx + 0.055 * s), by + 0.48 * s, bz + 0.37 * s, 0.002)]
            h = skin_object("horn", hn, [(0, 1), (1, 2), (2, 3), (3, 4)], 0, subsurf=1, decimate=0.5)
            parts.append(finish(h, bone, 0.05, lambda p, n: (0.85, 0.8, 0.76) if p.z < 2.3 else (1.04, 1.03, 1.0)))
    for sx in (1, -1):
        for k in range(3):
            z = 2.0 - k * 0.09
            parts.append(spike("neckspine", (sx * 0.07, 0.04, z), (sx * 0.12, 0.1, z - 0.03), 0.014, dark))
    for (y, z, s) in ((0.12, 1.98, 0.05), (0.18, 1.86, 0.05), (0.27, 1.32, 0.045), (0.27, 1.18, 0.045), (0.42, 0.92, 0.04),
                      (0.6, 0.66, 0.035), (0.78, 0.42, 0.03), (0.92, 0.2, 0.02)):
        parts.append(spike("dorsal", (0, y - 0.03, z), (0, y + s * 1.2, z + s * 0.6), s * 0.35, dark))
    return parts


# ----------------------------------------------------------------------------- crown and kit
def build_kit():
    gold = mat("Gold", GOLD, rough=0.5, metal=0.35)
    char = mat("Charcoal", CHARCOAL, rough=0.9)
    crim = mat("Crimson", CRIMSON, rough=0.9)
    leather = mat("Leather", LEATHER, rough=0.85)
    iron = mat("Iron", IRON, rough=0.6, metal=0.4)
    gem_m = mat("Garnet", "b31d2a", rough=0.15, emit="5a0a10", emit_strength=0.8)
    kit = []

    # crown: a black spiked band with a red gem at the front
    crown = loft("Crown", [(2.205, 0.108, 0.105, 0, -0.06), (2.255, 0.112, 0.11, 0, -0.06)], seg=10)
    kit.append(finish(crown, iron, 0.03))
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.48
        h = 0.11 if k == 3 else 0.075 - abs(k - 3) * 0.008
        p = (math.cos(a) * 0.11, -0.06 + math.sin(a) * 0.108, 2.245)
        kit.append(spike("crownspike", p, (p[0] * 1.08, p[1] - 0.005, p[2] + h), 0.02, iron, 4))
    kit.append(finish(prim("ico", "gem", (0, -0.172, 2.235), (0.018, 0.01, 0.028), subdivisions=1, radius=1), gem_m, 0.0))

    # gold breastplate: a front shell with sculpted planes and a diamond emblem
    bp = loft("Breastplate", [
        (1.26, 0.2, 0.17, 0, -0.005),
        (1.36, 0.21, 0.17, 0, -0.005),
        (1.5, 0.245, 0.19, 0, -0.02),
        (1.64, 0.27, 0.2, 0, -0.03),
        (1.78, 0.245, 0.18, 0, -0.01),
    ], arc=(math.radians(-200), math.radians(20)), seg=10, solidify=0.03)
    kit.append(finish(bp, gold, 0.05))
    for sx in (1, -1):
        kit.append(finish(prim("ico", "pec", (sx * 0.11, -0.21, 1.64), (0.11, 0.035, 0.08), (0, 0, sx * 0.1), subdivisions=1, radius=1), gold, 0.05))
    kit.append(finish(prim("cube", "ridge", (0, -0.235, 1.55), (0.012, 0.012, 0.16)), gold, 0.04))
    kit.append(finish(prim("cube", "emblem", (0, -0.245, 1.6), (0.045, 0.012, 0.045), (0, math.pi / 4, 0)), gold, 0.0))
    kit.append(finish(prim("cube", "emblem_gem", (0, -0.258, 1.6), (0.022, 0.008, 0.022), (0, math.pi / 4, 0)), gem_m, 0.0))
    # angular layered pauldrons
    for sx in (1, -1):
        for k, (dx, dz, s) in enumerate(((0.0, 0.0, 1.0), (0.06, -0.11, 0.8))):
            p = prim("ico", "pauldron", (sx * (0.36 + dx), 0.01, 1.8 + dz), (0.19 * s, 0.17 * s, 0.11 * s), (0, sx * (0.5 + k * 0.2), 0), subdivisions=1, radius=1)
            kit.append(finish(p, gold, 0.06))
    # charcoal mantle over the shoulders, open in a V at the front, gold-edged
    front_open = (math.radians(-90 + 32), math.radians(270 - 32))
    mantle = loft("Mantle", [(1.66, 0.43, 0.3, 0, 0.04, 0.03), (1.79, 0.36, 0.26, 0, 0.03, 0.02), (1.9, 0.17, 0.15, 0, 0.0)],
                  arc=front_open, seg=16, solidify=0.03)
    kit.append(finish(mantle, char, 0.05))
    hem = loft("MantleHem", [(1.64, 0.435, 0.305, 0, 0.04, 0.03), (1.69, 0.43, 0.3, 0, 0.04, 0.03)], arc=front_open, seg=16, solidify=0.035)
    kit.append(finish(hem, gold, 0.04))
    for sx in (1, -1):
        disc = prim("cyl", "clasp", (sx * 0.24, -0.27, 1.73), (0.06, 0.06, 0.018), (math.pi / 2, 0, 0), vertices=10)
        kit.append(finish(disc, gold, 0.03))
    # the cloak: charcoal outside, crimson inside, gold edges and hem
    arc = (math.radians(-28), math.radians(208))
    rings = [(1.82, 0.36, 0.24, 0, 0.05, 0.0), (1.5, 0.48, 0.32, 0, 0.11, 0.025), (1.0, 0.58, 0.4, 0, 0.16, 0.04),
             (0.5, 0.65, 0.45, 0, 0.2, 0.05), (0.2, 0.68, 0.48, 0, 0.22, 0.05)]
    cloak = loft("Cloak", list(reversed(rings)), arc=arc, seg=14, solidify=0.025)
    finish(cloak, char, 0.05)
    cloak.data.materials.append(crim)
    for p in cloak.data.polygons:
        c = p.center
        out = Vector((c.x, c.y - 0.12, 0)).normalized()
        if p.normal.dot(out) < -0.2:
            p.material_index = 1
    kit.append(cloak)
    trim = [(r[0], r[1] * 1.01, r[2] * 1.01, r[3], r[4], r[5]) for r in reversed(rings)]
    for a0, a1 in ((arc[0], arc[0] + 0.07), (arc[1] - 0.07, arc[1])):
        edge = loft("CloakEdge", trim, arc=(a0, a1), seg=1, solidify=0.035)
        kit.append(finish(edge, gold, 0.04))
    chem = loft("CloakHem", [(0.19, 0.685, 0.485, 0, 0.22, 0.05), (0.26, 0.676, 0.478, 0, 0.217, 0.05)], arc=arc, seg=14, solidify=0.035)
    kit.append(finish(chem, gold, 0.04))
    # belt, straps, kilt and tabard
    belt = loft("Belt", [(1.22, 0.205, 0.18, 0, 0.0), (1.3, 0.195, 0.17, 0, 0.0)], seg=12)
    kit.append(finish(belt, gold, 0.04))
    kit.append(finish(prim("cube", "buckle", (0, -0.185, 1.26), (0.05, 0.014, 0.045)), gold, 0.0))
    kilt = loft("Kilt", [(0.82, 0.33, 0.27, 0, 0.02, 0.04), (1.02, 0.28, 0.23, 0, 0.01, 0.03), (1.24, 0.2, 0.175, 0, 0.0)], seg=12)
    kit.append(finish(kilt, char, 0.05))
    khem = loft("KiltHem", [(0.81, 0.333, 0.273, 0, 0.02, 0.04), (0.85, 0.327, 0.268, 0, 0.02, 0.04)], seg=12)
    kit.append(finish(khem, gold, 0.04))
    tab = prim("cube", "tabard", (0, -0.25, 0.93), (0.1, 0.012, 0.3), (0.1, 0, 0))
    kit.append(finish(tab, char, 0.04))
    for sx in (1, -1):
        kit.append(finish(prim("cube", "tabtrim", (sx * 0.098, -0.252, 0.93), (0.012, 0.014, 0.3), (0.1, 0, 0)), gold, 0.0))
    kit.append(finish(prim("cube", "tabhem", (0, -0.22, 0.64), (0.11, 0.016, 0.014), (0.1, 0, 0)), gold, 0.0))
    kit.append(spike("tabpoint", (0, -0.215, 0.64), (0, -0.205, 0.58), 0.03, gold))
    for x in (-0.15, 0.15, -0.21, 0.21):
        st = prim("cube", "strap", (x, -0.2 + abs(x) * 0.35, 1.06), (0.03, 0.01, 0.2), (0.08, 0, x * 1.2))
        kit.append(finish(st, leather, 0.05))
    # vambraces
    for sx in (1, -1):
        vb = loft("Vambrace", [(1.1, 0.1, 0.095, sx * 0.502, -0.015), (1.2, 0.105, 0.1, sx * 0.49, 0.015), (1.31, 0.12, 0.115, sx * 0.478, 0.045)], seg=8)
        kit.append(finish(vb, gold, 0.05))
        kit.append(spike("vfin", (sx * 0.56, 0.06, 1.28), (sx * 0.6, 0.12, 1.33), 0.02, gold))
    return kit


# ----------------------------------------------------------------------------- stage and renders
def stage(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("Studio")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = hexc("8a5a48")
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    bpy.context.active_object.is_shadow_catcher = True

    def area(loc, rot, energy, size, color):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.active_object
        l.data.energy = energy
        l.data.size = size
        l.data.color = color
        l.rotation_euler = Euler([math.radians(v) for v in rot])
    area((-3.0, -3.2, 3.6), (50, 0, -42), 420, 2.5, (1.0, 0.84, 0.66))    # warm key, front-left
    area((3.2, -2.8, 1.8), (70, 0, 48), 90, 3.0, (0.85, 0.8, 0.95))       # cool fill
    area((2.4, 3.0, 3.0), (-55, 0, 145), 520, 1.5, (1.0, 0.66, 0.38))     # warm rim, behind-right


def shoot(path, loc, target, lens, res):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    cam = sc.camera
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        sc.camera = cam
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("render", path)


def orbit(target, dist, yaw_deg, pitch_deg):
    """Camera position around target: yaw 0 = straight in front, negative = toward the character's right."""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    t = Vector(target)
    return (t.x + math.sin(y) * math.cos(p) * dist, t.y - math.cos(y) * math.cos(p) * dist, t.z + math.sin(p) * dist)


def sheet(out, files):
    """Compose the character sheet: full figure left, four head studies right, palette swatches."""
    from PIL import Image, ImageDraw
    W, H = 1536, 1024
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(150 - 38 * t), int(96 - 28 * t), int(80 - 22 * t)))
    d.polygon([(0, 660), (700, 610), (700, H), (0, H)], fill=(134, 86, 70))
    d.line([(712, 476), (W, 476)], fill=(118, 74, 60), width=3)
    d.line([(705, 0), (705, H)], fill=(118, 74, 60), width=3)

    def paste(path, box):
        im = Image.open(path).convert("RGBA")
        bb = im.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
        if bb:
            im = im.crop((max(0, bb[0] - 20), max(0, bb[1] - 20), min(im.width, bb[2] + 20), min(im.height, bb[3] + 20)))
        scale = min(box[2] / im.width, box[3] / im.height)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        bg.paste(im, (box[0] + (box[2] - im.width) // 2, box[1] + (box[3] - im.height) // 2), im)
    paste(files["full"], (90, 10, 600, 1004))
    paste(files["h1"], (715, 8, 405, 462))
    paste(files["h2"], (1125, 8, 405, 462))
    paste(files["h3"], (715, 482, 405, 536))
    paste(files["h4"], (1125, 482, 405, 536))
    for i, h in enumerate(SWATCHES):
        cx, cy, r = 62, 78 + i * 66, 24
        rgb = tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=rgb, outline=(70, 46, 38))
    bg.save(out)
    print("sheet", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "renders"))
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = build_body() + build_head() + build_kit()
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
    print("Kharad parts:", len(parts), "triangles:", tris)
    os.makedirs(os.path.join(ROOT, "assets", "characters"), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    glb = os.path.join(ROOT, "assets", "characters", "kharad_thrask.glb")
    bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format="GLB", export_vertex_color="ACTIVE")
    print("exported", glb)
    if args.no_render:
        return
    os.makedirs(args.out, exist_ok=True)
    stage(args.samples)
    f = {k: os.path.join(args.out, "kharad_%s.png" % k) for k in ("full", "h1", "h2", "h3", "h4")}
    head = (0, -0.02, 2.14)
    shots = {
        "full": (orbit((0, 0, 1.2), 5.3, -28, 6), (0, 0, 1.2), 50, (860, 1300)),
        "h1": (orbit(head, 1.75, -38, 8), (0, -0.02, 2.08), 60, (700, 800)),
        "h2": (orbit(head, 1.75, -90, 4), (0, 0.04, 2.1), 60, (700, 800)),
        "h3": (orbit(head, 1.8, 0, 8), (0, -0.02, 2.07), 60, (700, 920)),
        "h4": (orbit(head, 1.8, -128, 16), (0, 0.02, 2.04), 55, (700, 920)),
    }
    for k, (loc, tgt, lens, res) in shots.items():
        if args.only and k != args.only:
            continue
        shoot(f[k], loc, tgt, lens, res)
    if not args.only:
        sheet(os.path.join(args.out, "kharad_sheet.png"), f)


if __name__ == "__main__":
    main()
