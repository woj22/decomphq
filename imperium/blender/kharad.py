"""Kharad warrior-king (Thrask of Khar-Dumeth), modelled procedurally in Blender.

Run:  python3 imperium/blender/kharad.py [--out DIR] [--samples N]
Writes renders (hero, back, head) to imperium/renders/ and a .glb to imperium/assets/characters/.

Style: faceted low-poly (flat shaded, decimated organic forms), warm sunset lighting.
Blender axes: Z up, the character faces -Y, +X is the character's left (screen right in front view).
"""
import argparse
import math
import os
import random

import bpy  # must come first: it provides bmesh and mathutils
import bmesh
from mathutils import Euler, Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = random.Random(7)

# ----------------------------------------------------------------------------- palette
SKIN = "5f6e43"
SKIN_DARK = "3c4a2c"
BELLY = "b4a46e"
HORN = "d9cba5"
BRONZE = "a8762f"
BRONZE_DARK = "7d5424"
CLOTH = "2c3a27"
CLOTH_LINING = "6e2a1e"
GOLD = "dcaa45"
LEATHER = "5e3f25"
IRON = "4b4c50"
EYE = "ffb21c"


def hexc(h, a=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


# ----------------------------------------------------------------------------- scene helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.75, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    # per-face colour variation from the "facet" attribute, multiplied onto the base colour
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


def finish(obj, material, jitter=0.07, region_fn=None):
    """Flat shading + a per-face colour attribute (facet jitter, optional regional tint)."""
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


# ----------------------------------------------------------------------------- organic forms via Skin
SKIN_K = 1.45   # skin radii are box half-sizes; subdivision shrinks them by roughly this much


def skin_object(name, nodes, edges, root=0, subsurf=1, decimate=0.5):
    """nodes: [(x, y, z, rx[, ry])]; edges: [(i, j)]. Returns a faceted low-poly mesh object."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([n[:3] for n in nodes], edges, [])
    obj = new_obj(name, me)
    obj.modifiers.new("skin", "SKIN")
    sv = me.skin_vertices[0].data
    for i, n in enumerate(nodes):
        rx = n[3] * SKIN_K
        ry = (n[4] if len(n) > 4 else n[3]) * SKIN_K
        sv[i].radius = (rx, ry)
        sv[i].use_root = i == root
    obj.modifiers["skin"].use_smooth_shade = False
    obj.modifiers["skin"].branch_smoothing = 0.6
    if subsurf:
        s = obj.modifiers.new("sub", "SUBSURF")
        s.levels = subsurf
        s.render_levels = subsurf
    if decimate < 1.0:
        d = obj.modifiers.new("dec", "DECIMATE")
        d.ratio = decimate
    apply_all(obj)
    return obj


def mirror_nodes(nodes, edges, side_nodes, side_edges):
    """Append a node chain for the character's left (+X) and its mirror (-X)."""
    out_nodes = list(nodes)
    out_edges = list(edges)
    for sign in (1, -1):
        base = len(out_nodes)
        remap = {}
        for k, n in enumerate(side_nodes):
            out_nodes.append((n[0] * sign, *n[1:]))
            remap[k] = base + k
        for a, b in side_edges:
            ia = a if isinstance(a, int) and a < 0 else None
            out_edges.append((remap[a] if not isinstance(a, str) else a, remap[b]))
    return out_nodes, out_edges


def loft(name, rings, closed=True, cap_top=False, cap_bottom=False, arc=None, solidify=0.0, subsurf=0):
    """rings: [(z, rx, ry, cx, cy)] lofted into a tube (or an open shell when arc=(a0, a1) radians)."""
    bm = bmesh.new()
    seg = 18
    vrings = []
    for (z, rx, ry, cx, cy, *rest) in rings:
        wob = rest[0] if rest else 0.0
        row = []
        n = seg if arc is None else seg + 1
        for i in range(n):
            t = (2 * math.pi * i / seg) if arc is None else arc[0] + (arc[1] - arc[0]) * i / seg
            f = 1.0 + (wob if i % 2 == 0 else -wob)
            row.append(bm.verts.new((cx + math.cos(t) * rx * f, cy + math.sin(t) * ry * f, z)))
        vrings.append(row)
    for a, b in zip(vrings, vrings[1:]):
        n = len(a)
        rng_ = range(n) if arc is None else range(n - 1)
        for i in rng_:
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_top and arc is None:
        bm.faces.new(vrings[-1])
    if cap_bottom and arc is None:
        bm.faces.new(list(reversed(vrings[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = new_obj(name, me)
    if subsurf:
        s = obj.modifiers.new("sub", "SUBSURF")
        s.levels = subsurf
    if solidify:
        s = obj.modifiers.new("sol", "SOLIDIFY")
        s.thickness = solidify
        s.offset = 0
    apply_all(obj)
    return obj


def prim(kind, name, loc, scale=(1, 1, 1), rot=(0, 0, 0), **kw):
    if kind == "cone":
        bpy.ops.mesh.primitive_cone_add(location=loc, rotation=rot, **kw)
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(location=loc, rotation=rot, **kw)
    elif kind == "ico":
        bpy.ops.mesh.primitive_ico_sphere_add(location=loc, rotation=rot, **kw)
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(location=loc, rotation=rot, **kw)
    elif kind == "cube":
        bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot, **kw)
    elif kind == "torus":
        bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


# ----------------------------------------------------------------------------- the Kharad
def build_body():
    # spine, neck, head, snout, jaw (centre line)
    nodes = [
        (0, 0.02, 0.98, 0.21, 0.19),   # 0 pelvis (root)
        (0, 0.00, 1.20, 0.23, 0.20),   # 1 belly
        (0, -0.02, 1.44, 0.29, 0.24),  # 2 chest
        (0, 0.01, 1.64, 0.27, 0.21),   # 3 upper chest
        (0, -0.05, 1.8, 0.115),        # 4 neck
        (0, -0.09, 1.92, 0.1),         # 5 neck top (inside the head)
        (0, -0.09, 1.92, 0.01),        # 6 (unused)
        (0, -0.09, 1.92, 0.01),        # 7 (unused)
        (0, -0.09, 1.92, 0.01),        # 8 (unused)
        (0, -0.09, 1.92, 0.01),        # 9 (unused)
        # tail
        (0, 0.20, 0.92, 0.17),         # 10
        (0, 0.47, 0.74, 0.135),        # 11
        (0, 0.78, 0.50, 0.10),         # 12
        (0, 1.08, 0.30, 0.07),         # 13
        (0, 1.34, 0.16, 0.042),        # 14
        (0, 1.52, 0.10, 0.015),        # 15
    ]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5),
             (0, 10), (10, 11), (11, 12), (12, 13), (13, 14), (14, 15)]
    # one side: arm and leg chains, attached to upper chest (3) and pelvis (0)
    side = [
        (0.22, 0.00, 1.66, 0.15),   # 0 clavicle
        (0.40, 0.02, 1.64, 0.15),   # 1 shoulder
        (0.50, 0.05, 1.32, 0.115),  # 2 elbow
        (0.55, -0.03, 1.06, 0.085),  # 3 wrist
        (0.57, -0.07, 0.97, 0.075),  # 4 palm
        (0.61, -0.12, 0.88, 0.03),   # 5 claw outer
        (0.57, -0.15, 0.87, 0.03),   # 6 claw mid
        (0.53, -0.13, 0.88, 0.03),   # 7 claw inner
        (0.51, -0.09, 0.98, 0.028),  # 8 thumb
        (0.15, 0.02, 0.96, 0.16),    # 9 hip
        (0.18, -0.09, 0.56, 0.125),  # 10 knee (forward)
        (0.19, 0.06, 0.16, 0.085),   # 11 ankle (back: digitigrade)
        (0.20, -0.08, 0.06, 0.08),   # 12 foot
        (0.25, -0.25, 0.035, 0.035),  # 13 toe out
        (0.20, -0.28, 0.035, 0.035),  # 14 toe mid
        (0.15, -0.25, 0.035, 0.035),  # 15 toe in
        (0.20, 0.10, 0.06, 0.03),    # 16 dewclaw
    ]
    side_edges = [("chest", 0), (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (4, 6), (4, 7), (3, 8),
                  ("pelvis", 9), (9, 10), (10, 11), (11, 12), (12, 13), (12, 14), (12, 15), (11, 16)]
    for sign in (1, -1):
        base = len(nodes)
        for n in side:
            nodes.append((n[0] * sign, *n[1:]))
        for a, b in side_edges:
            ia = 3 if a == "chest" else 0 if a == "pelvis" else base + a
            edges.append((ia, base + b))
    body = skin_object("KharadBody", nodes, edges, root=0, subsurf=1, decimate=0.42)

    skin = hexc(SKIN)

    def region(p, n):
        t = (1.0, 1.0, 1.0)
        # darker along the back and the top of the tail, pale belly/throat
        if n.y > 0.35 and p.z > 0.3:
            t = (0.72, 0.76, 0.7)
        if n.y < -0.3 and (0.9 < p.z < 1.75 and abs(p.x) < 0.2):
            t = (1.9, 1.7, 1.25)
        if p.z > 1.78 and n.z < -0.35:
            t = (1.8, 1.6, 1.2)
        return t
    finish(body, mat("KharadSkin", SKIN, rough=0.7), 0.09, region)
    return body


def loft_y(name, rings):
    """Loft along -Y (the snout): rings [(y, rx, rz, cz)]; both ends capped."""
    bm = bmesh.new()
    seg = 12
    vr = []
    for (y, rx, rz, cz) in rings:
        vr.append([bm.verts.new((math.cos(2 * math.pi * i / seg) * rx, y, cz + math.sin(2 * math.pi * i / seg) * rz)) for i in range(seg)])
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
    s2 = o.modifiers.new("sub", "SUBSURF")
    s2.levels = 1
    d = o.modifiers.new("dec", "DECIMATE")
    d.ratio = 0.55
    apply_all(o)
    return o


HEAD = [  # (y, rx, rz, cz): back of the skull to the tip of the snout
    (0.06, 0.07, 0.07, 2.0),
    (0.0, 0.125, 0.12, 2.02),
    (-0.1, 0.15, 0.13, 2.03),
    (-0.2, 0.135, 0.11, 2.02),
    (-0.3, 0.105, 0.085, 1.99),
    (-0.42, 0.085, 0.065, 1.97),
    (-0.5, 0.06, 0.05, 1.96),
    (-0.54, 0.03, 0.03, 1.955),
]
JAW = [(-0.02, 0.11, 0.06, 1.91), (-0.15, 0.115, 0.055, 1.9), (-0.3, 0.09, 0.042, 1.895), (-0.45, 0.06, 0.03, 1.895), (-0.5, 0.03, 0.02, 1.9)]


def head_at(y):
    """Interpolated head section (rx, rz, cz) at y."""
    for a, b in zip(HEAD, HEAD[1:]):
        if a[0] >= y >= b[0]:
            t = (a[0] - y) / (a[0] - b[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in (1, 2, 3))
    return HEAD[-1][1:]


def build_head_details():
    parts = []
    skin_m = mat("KharadSkin", SKIN, rough=0.7)
    dark_m = mat("KharadSkinDark", SKIN_DARK, rough=0.7)

    def head_region(p, n):
        if n.z < -0.3:
            return (1.7, 1.55, 1.15)
        if n.z > 0.5:
            return (0.8, 0.84, 0.78)
        return (1.0, 1.0, 1.0)
    parts.append(finish(loft_y("Head", HEAD), skin_m, 0.09, head_region))
    parts.append(finish(loft_y("Jaw", JAW), skin_m, 0.09, lambda p, n: (1.75, 1.6, 1.2) if n.z < 0 else (1, 1, 1)))
    # heavy brow ridge on the skull surface, eyes tucked beneath it
    for sx in (1, -1):
        rx, rz, cz = head_at(-0.2)
        b = prim("cone", "brow", (sx * rx * 0.6, -0.2, cz + rz * 0.78), (0.05, 0.075, 0.025), (math.pi / 2 + 0.25, 0, sx * -0.35), vertices=4)
        parts.append(finish(b, dark_m, 0.05))
        e = prim("ico", "eye", (sx * rx * 0.86, -0.225, cz + rz * 0.42), (0.03, 0.026, 0.022), subdivisions=1, radius=1)
        parts.append(finish(e, mat("KharadEye", EYE, rough=0.2, emit=EYE, emit_strength=3.0), 0.0))
        p = prim("cube", "pupil", (sx * (rx * 0.86 + 0.012), -0.25, cz + rz * 0.42), (0.004, 0.004, 0.018))
        parts.append(finish(p, mat("Black", "0d0a08", rough=0.3), 0.0))
        # nostrils and scale ridges
        rx2, rz2, cz2 = head_at(-0.5)
        n = prim("cube", "nostril", (sx * 0.025, -0.515, cz2 + rz2 * 0.6), (0.01, 0.012, 0.007))
        parts.append(finish(n, mat("Black", "0d0a08"), 0.0))
        # cheek frill
        f = prim("cone", "frill", (sx * 0.15, -0.02, 1.95), (0.05, 0.02, 0.09), (0.0, sx * 1.2, 0.0), vertices=4)
        parts.append(finish(f, dark_m, 0.06))
    # teeth along the upper lip
    for sx in (1, -1):
        for k in range(6):
            y = -0.2 - k * 0.055
            rx, rz, cz = head_at(y)
            t = prim("cone", "tooth", (sx * rx * 0.8, y, cz - rz * 0.85 - 0.012), (0.011, 0.011, 0.028 if k != 1 else 0.045), (math.pi, 0, 0), vertices=4)
            parts.append(finish(t, mat("Horn", HORN, rough=0.5), 0.05))
    # horns: curved, swept back (skin chains), a pair of big ones and two pairs of small
    horn_parts = []
    for sx in (1, -1):
        for (bx, by, bz, s) in ((0.11, -0.04, 2.1, 1.0), (0.14, 0.02, 2.02, 0.65), (0.06, 0.03, 2.13, 0.55)):
            hn = [(sx * bx, by, bz, 0.032 * s),
                  (sx * (bx + 0.06 * s), by + 0.12 * s, bz + 0.1 * s, 0.025 * s),
                  (sx * (bx + 0.1 * s), by + 0.27 * s, bz + 0.12 * s, 0.016 * s),
                  (sx * (bx + 0.11 * s), by + 0.4 * s, bz + 0.05 * s, 0.004)]
            h = skin_object("horn", hn, [(0, 1), (1, 2), (2, 3)], 0, subsurf=1, decimate=0.6)
            horn_parts.append(finish(h, mat("Horn", HORN, rough=0.5), 0.08))
    # dorsal spines down the neck, back and tail
    spines = []
    path = [(0, 0.08, 1.98), (0, 0.18, 1.86), (0, 0.24, 1.7), (0, 0.27, 1.48), (0, 0.25, 1.24),
            (0, 0.3, 0.98), (0, 0.52, 0.84), (0, 0.8, 0.6), (0, 1.08, 0.4), (0, 1.32, 0.24)]
    for k, p in enumerate(path):
        s = 0.07 - k * 0.004
        c = prim("cone", "spine", p, (s * 0.35, s, s * 1.2), (-0.9, 0, 0), vertices=4)
        spines.append(finish(c, mat("KharadSkinDark", SKIN_DARK), 0.08))
    return parts + horn_parts + spines


def build_kit():
    kit = []
    bronze = mat("Bronze", BRONZE, rough=0.42, metal=0.7)
    bronze_dark = mat("BronzeDark", BRONZE_DARK, rough=0.45, metal=0.8)
    gold = mat("Gold", GOLD, rough=0.25, metal=0.95)
    cloth = mat("Cloth", CLOTH, rough=0.9)
    leather = mat("Leather", LEATHER, rough=0.8)
    iron = mat("Iron", IRON, rough=0.45, metal=0.8)

    # muscled bronze cuirass
    cu = loft("Cuirass", [
        (1.04, 0.27, 0.24, 0, 0.0),
        (1.18, 0.29, 0.25, 0, -0.01),
        (1.36, 0.34, 0.29, 0, -0.03),
        (1.52, 0.37, 0.3, 0, -0.03),
        (1.64, 0.33, 0.26, 0, 0.0),
        (1.74, 0.2, 0.18, 0, 0.0),
    ], cap_top=False, subsurf=1)
    kit.append(finish(cu, bronze, 0.06))
    for z in (1.12, 1.24):
        band = loft("band", [(z, 0.3, 0.262, 0, -0.012), (z + 0.03, 0.305, 0.267, 0, -0.012)])
        kit.append(finish(band, bronze_dark, 0.03))
    # pectoral plates and a gorgon-ish boss
    boss = prim("ico", "boss", (0, -0.31, 1.36), (0.05, 0.02, 0.05), subdivisions=1, radius=1)
    kit.append(finish(boss, gold, 0.03))
    # gold collar
    col = loft("collar", [(1.7, 0.23, 0.2, 0, 0), (1.77, 0.19, 0.17, 0, 0)])
    kit.append(finish(col, gold, 0.04))
    # layered pauldrons
    for sx in (1, -1):
        for k in range(3):
            pa = prim("sphere", "pauldron", (sx * (0.4 + k * 0.025), 0.01, 1.7 - k * 0.07),
                      (0.17 - k * 0.01, 0.18 - k * 0.01, 0.1), (0, sx * 0.5, 0), segments=10, ring_count=6)
            kit.append(finish(pa, bronze if k % 2 == 0 else bronze_dark, 0.05))
    # under-skirt and pteruges
    sk = loft("skirt", [(0.66, 0.36, 0.31, 0, 0.0, 0.05), (0.86, 0.32, 0.28, 0, 0.0, 0.04), (1.07, 0.27, 0.24, 0, 0.0)], subsurf=0)
    kit.append(finish(sk, cloth, 0.06))
    for k in range(14):
        a = 2 * math.pi * k / 14
        x, y = math.cos(a) * 0.31, math.sin(a) * 0.27
        st = prim("cube", "pteryx", (x, y, 0.84), (0.045, 0.012, 0.2), (0, 0, a + math.pi / 2))
        st.rotation_euler = (0, 0, 0)
        kit.append(finish(st, leather, 0.08))
        tip = prim("cube", "pteryx_tip", (x * 1.02, y * 1.02, 0.645), (0.046, 0.014, 0.02), (0, 0, a + math.pi / 2))
        kit.append(finish(tip, gold, 0.03))
    belt = loft("belt", [(1.02, 0.3, 0.27, 0, 0), (1.07, 0.3, 0.27, 0, 0)])
    kit.append(finish(belt, gold, 0.04))
    # bracers and greaves
    for sx in (1, -1):
        br = loft("bracer", [(1.08, 0.125, 0.12, sx * 0.548, -0.035), (1.26, 0.15, 0.145, sx * 0.53, 0.012)])
        kit.append(finish(br, bronze, 0.05))
        gr = loft("greave", [(0.22, 0.135, 0.135, sx * 0.19, 0.03), (0.52, 0.17, 0.17, sx * 0.18, -0.07)])
        kit.append(finish(gr, bronze, 0.05))
    # the cloak: an open shell around the back, folds, gold hem, crimson lining
    rings = [
        (1.78, 0.42, 0.26, 0, 0.06, 0.0),
        (1.5, 0.5, 0.34, 0, 0.12, 0.04),
        (1.1, 0.6, 0.42, 0, 0.16, 0.06),
        (0.7, 0.68, 0.5, 0, 0.2, 0.07),
        (0.38, 0.74, 0.56, 0, 0.24, 0.08),
    ]
    cl = loft("Cloak", rings, arc=(math.radians(-20), math.radians(200)), solidify=0.025)
    cl.data.materials.append(cloth)
    finish(cl, cloth, 0.08)
    lining = mat("Lining", CLOTH_LINING, rough=0.9)
    cl.data.materials.append(lining)
    for p in cl.data.polygons:
        # faces whose normal points inward (toward the body) get the lining
        c = p.center
        out = Vector((c.x, c.y - 0.1, 0)).normalized()
        if p.normal.dot(Vector((out.x, out.y, 0))) < -0.2:
            p.material_index = 1
    kit.append(cl)
    hem = loft("hem", [(0.36, 0.745, 0.565, 0, 0.24, 0.08), (0.42, 0.735, 0.555, 0, 0.235, 0.08)], arc=(math.radians(-20), math.radians(200)), solidify=0.03)
    kit.append(finish(hem, gold, 0.04))
    mantle = loft("mantle", [(1.56, 0.5, 0.36, 0, 0.04, 0.05), (1.68, 0.44, 0.31, 0, 0.04, 0.04), (1.77, 0.3, 0.23, 0, 0.02, 0.03), (1.83, 0.16, 0.15, 0, -0.01)], subsurf=0)
    kit.append(finish(mantle, cloth, 0.07))
    for sx in (1, -1):
        clasp = prim("cyl", "clasp", (sx * 0.24, -0.27, 1.68), (0.05, 0.05, 0.015), (math.pi / 2, 0, 0), vertices=8)
        kit.append(finish(clasp, gold, 0.03))
    # iron crown with spikes and a garnet
    cr = loft("crown", [(2.1, 0.135, 0.15, 0, -0.08), (2.17, 0.145, 0.16, 0, -0.08)])
    kit.append(finish(cr, iron, 0.06))
    for k in range(9):
        a = 2 * math.pi * k / 9 + math.pi / 2
        sp = prim("cone", "crownspike", (math.cos(a) * 0.14, -0.08 + math.sin(a) * 0.155, 2.2), (0.02, 0.02, 0.05), vertices=4)
        kit.append(finish(sp, iron, 0.06))
    gem = prim("ico", "garnet", (0, -0.24, 2.135), (0.02, 0.012, 0.026), subdivisions=1, radius=1)
    kit.append(finish(gem, mat("Garnet", "9b1b24", rough=0.15, emit="5a0a10", emit_strength=0.6), 0.0))
    return kit


# ----------------------------------------------------------------------------- stage, lights, render
def stage(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 960
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    # sunset world: violet zenith, orange horizon
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
    cr.elements[0].position = 0.48
    cr.elements[0].color = hexc("d98a62")
    cr.elements[1].position = 0.62
    cr.elements[1].color = hexc("3b2f74")
    e = cr.elements.new(0.51)
    e.color = hexc("f2b27a")
    e2 = cr.elements.new(0.555)
    e2.color = hexc("b07aa6")
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    # marble floor
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    fl = bpy.context.active_object
    fm = bpy.data.materials.new("Marble")
    fm.use_nodes = True
    fnt = fm.node_tree
    chk = fnt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value = 7.0
    chk.inputs["Color1"].default_value = hexc("e6d8c0")
    chk.inputs["Color2"].default_value = hexc("c9b498")
    fnt.links.new(chk.outputs["Color"], fnt.nodes["Principled BSDF"].inputs["Base Color"])
    fnt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.35
    fl.data.materials.append(fm)
    # low warm sun from behind-left, cool fill, rim
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    sun = bpy.context.active_object
    sun.data.energy = 4.0
    sun.data.color = (1.0, 0.68, 0.42)
    sun.data.angle = math.radians(3)
    sun.rotation_euler = Euler((math.radians(70), 0, math.radians(-130)))
    bpy.ops.object.light_add(type="AREA", location=(2.5, -3.5, 2.6))
    fill = bpy.context.active_object
    fill.data.energy = 220
    fill.data.size = 3
    fill.data.color = (0.75, 0.7, 1.0)
    fill.rotation_euler = Euler((math.radians(60), 0, math.radians(35)))
    bpy.ops.object.light_add(type="AREA", location=(-2.2, 2.4, 3.0))
    rim = bpy.context.active_object
    rim.data.energy = 260
    rim.data.size = 2
    rim.data.color = (1.0, 0.75, 0.5)
    rim.rotation_euler = Euler((math.radians(-55), 0, math.radians(-140)))


def shoot(path, loc, target, lens=50):
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        sc.camera = cam
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("render", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "renders"))
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    reset()
    body = build_body()
    details = build_head_details()
    kit = build_kit()
    allp = [body] + details + kit
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in allp)
    print("Kharad parts:", len(allp), "triangles:", tris)
    # export the character (before adding the stage)
    os.makedirs(os.path.join(ROOT, "assets", "characters"), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in allp:
        o.select_set(True)
    glb = os.path.join(ROOT, "assets", "characters", "kharad_thrask.glb")
    bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format="GLB", export_vertex_color="ACTIVE")
    print("exported", glb)
    if args.no_render:
        return
    stage(args.samples)
    os.makedirs(args.out, exist_ok=True)
    shoot(os.path.join(args.out, "kharad_front.png"), (2.2, -4.6, 2.0), (0, 0, 1.15), 50)
    shoot(os.path.join(args.out, "kharad_back.png"), (-3.4, 3.6, 1.9), (0, 0.2, 1.0), 50)
    shoot(os.path.join(args.out, "kharad_head.png"), (0.75, -1.35, 2.15), (0, -0.2, 1.95), 70)


if __name__ == "__main__":
    main()
