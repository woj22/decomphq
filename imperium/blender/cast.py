"""The court of Imperium, hand-placed low-poly, built from one data table.

Run:  python3 imperium/blender/cast.py [--only id,id] [--samples N] [--no-render]
Writes renders/cast_<group>.png line-ups, renders/cast_<id>.png turnarounds (with --turn) and
assets/characters/<id>.glb.

Every body is a stack of hand-drawn cross-sections (8-point rings: front, front corners, sides,
back corners, back) with limbs as six-sided tubes along joint paths. Heads per species are built the
same way; the Kharad uses the approved hand-modelled head (kharad_head.py). Flat colours throughout.
Axes: Z up, characters face -Y, +X is the character's left.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import kharad as K  # noqa: E402
import kharad_head as KH  # noqa: E402

ROOT = K.ROOT
GOLD, SILVER, IRON, LEATHER, BONE = "c8862d", "c7cdd8", "3a373b", "5b3a28", "e2d3c3"

# ----------------------------------------------------------------------------- the cast
# outfit: toga | tunic | robe | stola | armour | scale.  headwear: laurel_gold, crown_gold, crown_silver,
# crown_iron, diadem, diadem_silver, circlet, circlet_gold, helmet, none.
CAST = {
    "emperor": dict(name="Aurex IV Valerran", title="Emperor", species="human", sex="m", group="imperial",
                    skin="d8a77f", hair="8e8a84", hair_style="short", beard="short", outfit="toga",
                    primary="efe6d2", secondary="5a1f5c", trim=GOLD, cloak="8e1f24", headwear="laurel_gold", prop="staff_gold", build=1.06),
    "empress": dict(name="Sabine Valerran", title="Empress", species="human", sex="f", group="imperial",
                    skin="e9c4a0", hair="a87a45", hair_style="bun", outfit="stola", primary="7a3a6a", secondary="efe6d2", trim=GOLD, headwear="diadem"),
    "prince": dict(name="Valen Valerran", title="Crown Prince", species="human", sex="m", group="imperial",
                   skin="d8a77f", hair="6b4424", hair_style="curly", outfit="tunic", primary="efe6d2", secondary="5a1f5c", trim=GOLD,
                   cloak="8a2a3a", headwear="diadem", prop="sword"),
    "chancellor": dict(name="Severa Ostian", title="Prefect of the Palace", species="human", sex="f", group="ministers",
                       skin="c08a62", hair="d9d6d0", hair_style="bun", outfit="stola", primary="3d4a5c", secondary="c9c2b0", trim=GOLD, prop="tablet"),
    "treasurer": dict(name="Nyssal Vey-Tamir", title="Count of the Treasury", species="veyari", sex="m", group="ministers",
                      skin="8fa8cc", hair="e8ecf2", hair_style="long", outfit="robe", primary="1f5f66", secondary="c9d3e6", trim=SILVER,
                      headwear="circlet", prop="tablet"),
    "thane": dict(name="Decimar Thane", title="Marshal of the Legions", species="human", sex="m", group="ministers",
                  skin="c08a62", hair="1e1712", hair_style="cropped", outfit="armour", primary="b8893a", secondary="9b2226", trim=GOLD,
                  cloak="9b2226", headwear="helmet", prop="sword", build=1.06),
    "korrach": dict(name="Korrach Venn", title="Legate of the Auxilia", species="kharad", sex="m", group="ministers",
                    skin="4b5a4f", outfit="scale", primary="7d8790", secondary="2f3b2a", trim="b07a3a", cloak="2f3b2a", prop="spear"),
    "ulda": dict(name="Ulda Karrask", title="Master of Imperial Works", species="othari", sex="f", group="ministers",
                 skin="9a7b62", hair="b0a090", hair_style="braids", beard="plates", outfit="tunic", primary="a0602a", secondary="5c4a3a",
                 trim="c9b48a", prop="tablet"),
    "halvana": dict(name="Halvana Pryce", title="Governor of Meridia", species="human", sex="f", group="ministers",
                    skin="c08a62", hair="3a2618", hair_style="bun", outfit="stola", primary="5f7a3a", secondary="efe6d2", trim="c9b48a", prop="scroll"),
    "herald": dict(name="Sethiel Aurn", title="Imperial Herald", species="veyari", sex="m", group="ministers",
                   skin="b2a6d6", hair="b9c4d6", hair_style="long", outfit="robe", primary="efe6d2", secondary="5a1f5c", trim=GOLD,
                   cloak="8e1f24", prop="staff"),
    "cassia": dict(name="Cassia Varro", title="Praetorian Prefect", species="human", sex="f", group="ministers",
                   skin="9a6744", hair="1e1712", hair_style="cropped", outfit="armour", primary="aeb4bc", secondary="5a1f5c", trim=GOLD,
                   cloak="8e1f24", headwear="helmet", prop="spear", shield="8e1f24"),
    "thrask": dict(name="Thrask Ur-Vashen", title="King of Khar-Dumeth", species="kharad", sex="m", group="kings",
                   skin="5b6235", outfit="armour", primary=GOLD, secondary="38333a", trim=GOLD, cloak="38333a", lining="7f1d24",
                   headwear="kharad_crown", build=1.06),
    "marcellan": dict(name="Marcellan Dorr", title="King of Lucerna", species="human", sex="m", group="kings",
                      skin="e9c4a0", hair="1e1712", hair_style="short", beard="full", outfit="toga", primary="efe6d2", secondary="c8702a",
                      trim=GOLD, cloak="c8702a", headwear="crown_gold", build=1.06),
    "vashka": dict(name="Vashka Tor-Ilun", title="Queen of Tor-Ilun", species="kharad", sex="f", group="kings",
                   skin="7a6a48", outfit="tunic", primary="7a2e1c", secondary="c9b48a", trim=GOLD, cloak="c9b48a", build=0.94),
    "ilsaveth": dict(name="Ilsaveth Anorai", title="Queen of Velithra", species="veyari", sex="f", group="kings",
                     skin="a9bce0", hair="e8ecf2", hair_style="long", outfit="robe", primary="1f6f78", secondary="c9d3e6", trim=SILVER,
                     cloak="c9d3e6", headwear="diadem_silver"),
    "oduvar": dict(name="Oduvar Brunnhak", title="King of Karst Odun", species="othari", sex="m", group="kings",
                   skin="8a8580", hair="3a3430", hair_style="braids", beard="plates", outfit="tunic", primary="8a4b24", secondary="5a5d63",
                   trim="c9b48a", cloak="5a5d63", headwear="crown_iron", build=1.06),
    "player": dict(name="Cassian Arvel", title="King of Seravel (you)", species="human", sex="m", group="household",
                   skin="d8a77f", hair="3a2618", hair_style="short", beard="short", outfit="toga", primary="e8e2d4", secondary="2b4c7e",
                   trim=SILVER, cloak="2b4c7e", headwear="crown_silver"),
    "aldric": dict(name="Aldric Fenn", title="Royal Steward", species="human", sex="m", group="household",
                   skin="e9c4a0", hair="d9d6d0", hair_style="short", beard="short", outfit="robe", primary="2b4c7e", secondary="c7cdd8",
                   trim=SILVER, prop="scroll"),
    "hessa": dict(name="Hessa Durn", title="Captain of the Seravel Guard", species="othari", sex="f", group="household",
                  skin="6f6a66", hair="2a2826", hair_style="braids", beard="plates", outfit="armour", primary="8e9196", secondary="2b4c7e",
                  trim=SILVER, cloak="2b4c7e", headwear="helmet", prop="spear", shield="2b4c7e"),
}
GROUPS = [("imperial", "The Imperial House"), ("ministers", "Ministers & Officers"), ("kings", "The Client Kings"), ("household", "Your Household")]

# Body plans: joint heights (m), torso half-widths and depth, limb radii, head kind and scale.
SPECIES = {
    "human": dict(ankle=0.09, knee=0.5, hip=0.92, waist=1.1, chest=1.3, shoulder=1.44, neck=1.51, neck_top=1.58,
                  hip_w=0.16, waist_w=0.145, chest_w=0.19, sh_w=0.215, depth=0.12, leg=(0.078, 0.058, 0.044), arm=(0.056, 0.046, 0.036),
                  arm_x=0.205, leg_x=0.09, neck_r=0.055, head=1.14, foot=0.16),
    "veyari": dict(ankle=0.1, knee=0.57, hip=1.03, waist=1.22, chest=1.43, shoulder=1.57, neck=1.65, neck_top=1.76,
                   hip_w=0.14, waist_w=0.125, chest_w=0.165, sh_w=0.19, depth=0.105, leg=(0.068, 0.05, 0.038), arm=(0.048, 0.04, 0.031),
                   arm_x=0.18, leg_x=0.08, neck_r=0.048, head=1.1, foot=0.15),
    "othari": dict(ankle=0.08, knee=0.32, hip=0.6, waist=0.78, chest=0.98, shoulder=1.14, neck=1.2, neck_top=1.24,
                   hip_w=0.21, waist_w=0.21, chest_w=0.26, sh_w=0.29, depth=0.17, leg=(0.1, 0.085, 0.07), arm=(0.075, 0.065, 0.055),
                   arm_x=0.29, leg_x=0.12, neck_r=0.08, head=1.22, foot=0.18),
    "kharad": dict(ankle=0.32, knee=0.72, hip=1.1, waist=1.3, chest=1.56, shoulder=1.74, neck=1.8, neck_top=1.98,
                   hip_w=0.2, waist_w=0.18, chest_w=0.27, sh_w=0.3, depth=0.17, leg=(0.12, 0.085, 0.06), arm=(0.085, 0.068, 0.055),
                   arm_x=0.32, leg_x=0.15, neck_r=0.12, head=1.0, foot=0.3),
}


# ----------------------------------------------------------------------------- materials and mesh helpers
def m(hexcol, rough=0.85, metal=0.0, emit=None, strength=0.0):
    return K.mat("C_%s_%d_%d" % (hexcol, int(rough * 10), int(metal * 10)), hexcol, rough, metal, emit, strength)


def metal(hexcol):
    return m(hexcol, 0.45, 0.45)


def done(obj, mat, region=None, mats=None):
    """Flat shading, flat colour; optional per-face material choice."""
    me = obj.data
    me.materials.clear()
    for mm in [mat] + (mats or []):
        me.materials.append(mm)
    for p in me.polygons:
        p.use_smooth = False
        if region:
            p.material_index = region(p.center, p.normal)
    if "facet" not in me.color_attributes:
        ca = me.color_attributes.new("facet", "BYTE_COLOR", "CORNER")
        for dd in ca.data:
            dd.color = (1, 1, 1, 1)
    return obj


def mesh_from(name, verts, faces, tri_nonplanar=True):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if tri_nonplanar:
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3 and not _planar(f)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return K.new_obj(name, me)


def _planar(f, tol=0.0015):
    n = f.normal
    p0 = f.verts[0].co
    return all(abs((v.co - p0).dot(n)) < tol for v in f.verts)


def ring8(w, f, b):
    """Hand-drawn 8-point section: front centre, front corners, sides, back corners, back centre."""
    return [(0, -f), (0.7 * w, -0.86 * f), (w, -0.12 * f), (0.82 * w, 0.72 * b), (0, b), (-0.82 * w, 0.72 * b), (-w, -0.12 * f), (-0.7 * w, -0.86 * f)]


def ringN(n, rx, ry, fold=0.0, phase=0.0):
    return [(math.cos(phase + 2 * math.pi * i / n) * rx * (1 + (fold if i % 2 else -fold)),
             math.sin(phase + 2 * math.pi * i / n) * ry * (1 + (fold if i % 2 else -fold))) for i in range(n)]


def stack(name, sections, cap_bottom=True, cap_top=True, arc_open=None):
    """sections: [(z, [(x, y), ...], cx, cy)] with equal point counts; joined into planes."""
    verts, faces = [], []
    n = len(sections[0][1])
    for (z, pts, cx, cy) in sections:
        verts += [(cx + x, cy + y, z) for (x, y) in pts]
    for k in range(len(sections) - 1):
        a, b = k * n, (k + 1) * n
        for i in range(n if arc_open is None else n - 1):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    if cap_bottom and arc_open is None:
        faces.append(tuple(reversed(range(n))))
    if cap_top and arc_open is None:
        last = (len(sections) - 1) * n
        faces.append(tuple(range(last, last + n)))
    return mesh_from(name, verts, faces)


def tube(name, path, radii, sides=6, flat_y=1.0):
    """Few-sided tube along a joint path (limbs, horns, poles), capped."""
    pts = [Vector(p) for p in path]
    verts, faces = [], []
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        ref = Vector((0, -1, 0)) if abs(t.y) < 0.9 else Vector((1, 0, 0))
        u = (ref - t * ref.dot(t)).normalized()
        v = t.cross(u).normalized()
        for i in range(sides):
            a = 2 * math.pi * i / sides + math.pi / sides
            verts.append(tuple(p + (u * math.cos(a) * flat_y + v * math.sin(a)) * radii[k]))
    for k in range(len(pts) - 1):
        a, b = k * sides, (k + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((a + i, a + j, b + j, b + i))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range((len(pts) - 1) * sides, len(pts) * sides)))
    return mesh_from(name, verts, faces)


def block(name, center, size, rot=(0, 0, 0), taper=1.0):
    """A box (optionally tapering toward +Z) - for hands, feet, plates, buckles."""
    cx, cy, cz = center
    sx, sy, sz = (s / 2 for s in size)
    vs = []
    for z, k in ((-sz, 1.0), (sz, taper)):
        vs += [(-sx * k, -sy * k, z), (sx * k, -sy * k, z), (sx * k, sy * k, z), (-sx * k, sy * k, z)]
    mat = (Matrix.Rotation(rot[2], 3, "Z") @ Matrix.Rotation(rot[1], 3, "Y") @ Matrix.Rotation(rot[0], 3, "X"))
    vs = [tuple(mat @ Vector(v) + Vector(center)) for v in vs]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh_from(name, vs, faces)


def pyramid(name, base_pts, tip):
    vs = [tuple(p) for p in base_pts] + [tuple(tip)]
    n = len(base_pts)
    faces = [tuple(reversed(range(n)))] + [(i, (i + 1) % n, n) for i in range(n)]
    return mesh_from(name, vs, faces)


def spike(name, base, tip, r, sides=4):
    base, tip = Vector(base), Vector(tip)
    t = (tip - base).normalized()
    u = t.cross(Vector((0, 0, 1)))
    if u.length < 1e-3:
        u = Vector((1, 0, 0))
    u.normalize()
    v = t.cross(u)
    pts = [base + (u * math.cos(2 * math.pi * i / sides) + v * math.sin(2 * math.pi * i / sides)) * r for i in range(sides)]
    return pyramid(name, pts, tip)


def shell(name, sections, a0, a1, thickness=0.02, segs=10):
    """An open curved panel (cloaks, capes, beards): sections [(z, rx, ry, cx, cy)] between angles a0..a1."""
    verts, faces = [], []
    for (z, rx, ry, cx, cy) in sections:
        for i in range(segs + 1):
            t = a0 + (a1 - a0) * i / segs
            verts.append((cx + math.cos(t) * rx, cy + math.sin(t) * ry, z))
    n = segs + 1
    for k in range(len(sections) - 1):
        for i in range(segs):
            faces.append((k * n + i, k * n + i + 1, (k + 1) * n + i + 1, (k + 1) * n + i))
    o = mesh_from(name, verts, faces, tri_nonplanar=False)
    if thickness:
        s = o.modifiers.new("sol", "SOLIDIFY")
        s.thickness = thickness
        s.offset = 0
        K.apply_all(o)
    return o


# ----------------------------------------------------------------------------- builder
class Figure:
    def __init__(self, cid, spec, x=0.0):
        self.id = cid
        self.s = spec
        self.sp = dict(SPECIES[spec["species"]])
        b = spec.get("build", 1.0)
        fem = spec.get("sex") == "f"
        for k in ("hip_w", "waist_w", "chest_w", "sh_w", "depth"):
            self.sp[k] *= b
        if fem:
            self.sp["sh_w"] *= 0.86
            self.sp["chest_w"] *= 0.9
            self.sp["hip_w"] *= 1.08
            self.sp["waist_w"] *= 0.88
            self.sp["arm"] = tuple(r * 0.88 for r in self.sp["arm"])
        self.parts = []
        self.ox = x

    def add(self, obj):
        obj.location.x += self.ox
        self.parts.append(obj)
        return obj

    # colours
    def c(self, key, default="808080"):
        v = self.s.get(key)
        return v if v else default

    @property
    def skin(self):
        return m(self.s["skin"], 0.85)

    def build(self):
        sp = self.sp
        o = self.s["outfit"]
        kh = self.s["species"] == "kharad"
        long_skirt = o in ("toga", "robe", "stola")
        armoured = o in ("armour", "scale")
        self.torso(armoured)
        self.legs(long_skirt, armoured)
        self.arms(o, armoured)
        self.skirt(o)
        if kh:
            self.tail()
        self.head()
        self.headwear()
        if self.s.get("cloak"):
            self.cloak()
        self.props()
        return self.parts

    # ------------------------------------------------------------------ torso
    def torso(self, armoured):
        sp = self.sp
        d = sp["depth"]
        prim = self.c("primary")
        under = self.c("secondary") if self.s["outfit"] == "toga" else prim
        if self.s["species"] == "othari" and self.s["outfit"] != "armour":
            under = prim
        secs = [
            (sp["hip"] - 0.05, ring8(sp["hip_w"] * 0.94, d * 0.92, d * 0.95), 0, 0),
            (sp["hip"] + 0.06, ring8(sp["hip_w"], d, d * 1.05), 0, 0),
            (sp["waist"], ring8(sp["waist_w"], d * 0.94, d * 0.86), 0, 0),
            (sp["chest"], ring8(sp["chest_w"], d * 1.12, d * 0.96), 0, -0.005),
            (sp["shoulder"], ring8(sp["sh_w"], d * 0.92, d * 0.86), 0, 0),
            (sp["neck"], ring8(sp["sh_w"] * 0.42, d * 0.55, d * 0.6), 0, 0),
        ]
        t = stack("Torso", secs)
        if armoured:
            done(t, self.skin)
            self.add(t)
            self.cuirass()
        else:
            col = m(under)
            # the chest panel carries a trim stripe down the front
            done(t, col)
            self.add(t)
            self.add(done(block("Belt", (0, 0, sp["waist"] - 0.01), (sp["waist_w"] * 2.1, d * 1.95, 0.05)), metal(self.c("trim"))))
            if self.s["outfit"] == "toga":
                self.toga_sash()
            elif self.s["outfit"] == "stola":
                self.palla()
            elif self.s["outfit"] in ("robe", "tunic"):
                for sx in ((0,) if self.s["outfit"] == "robe" else (-0.06, 0.06)):
                    self.add(done(block("Clavus", (sx, -d * 1.08, (sp["waist"] + sp["shoulder"]) / 2), (0.03, 0.01, sp["shoulder"] - sp["waist"])), m(self.c("secondary"))))
        # neck
        kh = self.s["species"] == "kharad"
        if not kh:
            n = tube("Neck", [(0, 0, sp["neck"] - 0.04), (0, -0.005, sp["neck_top"] + 0.02)], [sp["neck_r"] * 1.1, sp["neck_r"]], 6)
        else:
            n = tube("Neck", [(0, 0.0, sp["neck"] - 0.06), (0, -0.02, sp["neck"] + 0.08), (0, -0.04, sp["neck_top"])], [0.15, 0.13, 0.115], 8)
        self.add(done(n, self.skin))

    def cuirass(self):
        sp = self.sp
        d = sp["depth"]
        met = metal(self.c("primary"))
        k = 1.12
        secs = [
            (sp["waist"] - 0.1, ring8(sp["waist_w"] * 1.12, d * 1.1, d * 1.05), 0, 0),
            (sp["waist"], ring8(sp["waist_w"] * k, d * 0.98 * k, d * 0.9 * k), 0, 0),
            (sp["chest"], ring8(sp["chest_w"] * k, d * 1.16 * k, d * 1.0 * k), 0, -0.005),
            (sp["shoulder"] - 0.01, ring8(sp["sh_w"] * 1.02, d * 0.98 * k, d * 0.9 * k), 0, 0),
            (sp["neck"] - 0.02, ring8(sp["sh_w"] * 0.5, d * 0.66, d * 0.66), 0, 0),
        ]
        cu = stack("Cuirass", secs, cap_top=False)
        self.add(done(cu, met))
        cz = sp["chest"]
        self.add(done(block("Emblem", (0, -d * 1.32, cz - 0.1), (0.05, 0.02, 0.05), (0, math.pi / 4, 0)), metal(self.c("trim"))))
        self.add(done(block("Emblem2", (0, -d * 1.345, cz - 0.1), (0.025, 0.01, 0.025), (0, math.pi / 4, 0)), m("b31d2a", 0.2)))
        # bands at the waist (scale armour: rows of plates)
        rows = 4 if self.s["outfit"] == "scale" else 1
        for r in range(rows):
            z = sp["waist"] - 0.06 + r * (sp["chest"] - sp["waist"]) / max(rows, 1) * 0.9
            band = stack("Band", [(z, ring8(sp["waist_w"] * 1.2 + r * 0.012, d * 1.16, d * 1.1), 0, 0),
                                  (z + 0.035, ring8(sp["waist_w"] * 1.2 + r * 0.012, d * 1.16, d * 1.1), 0, 0)])
            self.add(done(band, metal(self.c("trim")) if rows == 1 else m(self.c("primary"), 0.5, 0.3)))
        # pauldrons: two stepped angular plates per shoulder
        for sx in (1, -1):
            for k2, (dz, s2) in enumerate(((0.0, 1.0), (-0.09, 0.82))):
                x0 = sx * (sp["arm_x"] + 0.01 + k2 * 0.03)
                z0 = sp["shoulder"] + 0.02 + dz
                w = sp["arm"][0] * 2.2 * s2
                vs = [(x0 - sx * w * 0.6, -w * 0.9, z0 + 0.03), (x0 + sx * w * 0.7, -w * 0.8, z0 - 0.06), (x0 + sx * w * 0.7, w * 0.8, z0 - 0.06),
                      (x0 - sx * w * 0.6, w * 0.9, z0 + 0.03), (x0 + sx * w * 0.05, 0, z0 + 0.09)]
                fs = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)]
                self.add(done(mesh_from("Pauldron", vs, fs), metal(self.c("primary")) if k2 == 0 else metal(self.c("trim"))))

    def toga_sash(self):
        sp = self.sp
        d = sp["depth"]
        path = [(sp["hip_w"] * 0.7, -d * 1.05, sp["hip"] + 0.02), (0.0, -d * 1.2, (sp["waist"] + sp["chest"]) / 2),
                (-sp["chest_w"] * 0.7, -d * 1.12, sp["shoulder"] - 0.02), (-sp["sh_w"] * 0.75, 0.0, sp["shoulder"] + 0.03),
                (-sp["chest_w"] * 0.6, d * 1.15, sp["chest"]), (-sp["hip_w"] * 0.4, d * 1.15, sp["hip"] - 0.05)]
        self.add(done(tube("Sash", path, [0.07, 0.08, 0.075, 0.07, 0.075, 0.075], 4, 0.45), m(self.c("primary"))))
        stripe = [(x + 0.03, y - 0.02 if y < 0 else y + 0.02, z) for (x, y, z) in path]
        self.add(done(tube("SashStripe", stripe, [0.02] * len(path), 4, 0.5), m(self.c("secondary"))))

    def palla(self):
        sp = self.sp
        d = sp["depth"]
        secs = [(sp["chest"] - 0.04, sp["sh_w"] * 1.2, d * 1.5, 0, 0.0), (sp["shoulder"] + 0.02, sp["sh_w"] * 1.12, d * 1.25, 0, 0.0),
                (sp["neck"] + 0.01, sp["sh_w"] * 0.62, d * 0.85, 0, 0.0)]
        pl = shell("Palla", secs, math.radians(-90 + 35), math.radians(270 - 35), 0.03, 12)
        self.add(done(pl, m(self.c("secondary"))))

    # ------------------------------------------------------------------ limbs
    def legs(self, long_skirt, armoured):
        sp = self.sp
        kh = self.s["species"] == "kharad"
        r = sp["leg"]
        for sx in (1, -1):
            x = sx * sp["leg_x"]
            if kh:
                path = [(x, 0.02, sp["hip"] + 0.02), (x * 1.1, -0.13, sp["knee"]), (x * 1.18, 0.1, sp["ankle"]), (x * 1.22, -0.05, 0.07)]
                leg = tube("Leg", path, [r[0], r[1], r[2], r[2] * 0.9], 6)
                self.add(done(leg, self.skin))
                for k, dx in enumerate((-0.05, 0.0, 0.05)):
                    tp = Vector((x * 1.22 + dx, -0.3 + abs(dx) * 0.6, 0.03))
                    toe = tube("Toe", [(x * 1.22 + dx * 0.4, -0.06, 0.06), tuple(tp)], [0.04, 0.028], 4)
                    self.add(done(toe, self.skin))
                    self.add(done(spike("Claw", tp + Vector((0, 0.01, 0)), tp + Vector((0, -0.08, -0.025)), 0.022), m(BONE, 0.5)))
                continue
            path = [(x, 0.0, sp["hip"] + 0.02), (x * 1.04, -0.012, sp["knee"]), (x * 1.06, 0.01, sp["ankle"])]
            col = self.skin
            self.add(done(tube("Leg", path, list(r), 6), col))
            # foot: a tapering wedge, sandal-brown (or a boot for soldiers)
            fl = sp["foot"]
            foot = mesh_from("Foot", [(x - 0.045, 0.04, 0.0), (x + 0.045, 0.04, 0.0), (x + 0.04, -fl, 0.0), (x - 0.04, -fl, 0.0),
                                      (x - 0.04, 0.035, sp["ankle"] + 0.01), (x + 0.04, 0.035, sp["ankle"] + 0.01), (x + 0.03, -fl + 0.02, 0.045), (x - 0.03, -fl + 0.02, 0.045)],
                             [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
            self.add(done(foot, m("5c3d24") if not armoured else m("3d2a1e")))
            if armoured and not long_skirt:
                g = tube("Greave", [(x * 1.06, -0.005, sp["ankle"] + 0.05), (x * 1.04, -0.02, sp["knee"] + 0.02)], [r[2] * 1.3, r[1] * 1.25], 6)
                self.add(done(g, metal(self.c("primary"))))

    def arms(self, outfit, armoured):
        sp = self.sp
        r = sp["arm"]
        kh = self.s["species"] == "kharad"
        for sx in (1, -1):
            sh = (sx * sp["arm_x"], 0.0, sp["shoulder"] - 0.02)
            el = (sx * (sp["arm_x"] + 0.06), 0.03, sp["waist"] + 0.03)
            wr = (sx * (sp["arm_x"] + 0.09), -0.01, sp["hip"] - 0.0)
            sleeve_col = None
            fore_col = self.skin
            if outfit in ("robe", "stola") or (outfit == "toga" and sx < 0):
                sleeve_col = m(self.c("primary"))
                fore_col = sleeve_col
            elif outfit == "tunic":
                sleeve_col = m(self.c("primary"))
            elif outfit == "toga":
                sleeve_col = m(self.c("secondary"))
            upper = tube("UpperArm", [sh, el], [r[0], r[1]], 6)
            self.add(done(upper, self.skin))
            if sleeve_col:
                mid = tuple((Vector(sh) * 0.45 + Vector(el) * 0.55))
                self.add(done(tube("Sleeve", [(sh[0], sh[1], sh[2] + 0.02), mid], [r[0] * 1.3, r[0] * 1.25], 6), sleeve_col))
            fore = tube("Forearm", [el, wr], [r[1], r[2]], 6)
            self.add(done(fore, fore_col))
            if outfit in ("robe", "stola"):
                cuff = tube("Cuff", [tuple(Vector(el).lerp(Vector(wr), 0.55)), tuple(Vector(wr) + Vector((0, 0, -0.01)))], [r[1] * 1.25, r[2] * 1.7], 6)
                self.add(done(cuff, fore_col))
            if armoured:
                vb = tube("Vambrace", [tuple(Vector(el).lerp(Vector(wr), 0.35)), tuple(Vector(wr) + Vector((0, 0, 0.02)))], [r[1] * 1.3, r[2] * 1.35], 6)
                self.add(done(vb, metal(self.c("trim"))))
            # hand: a tapered mitten with a thumb wedge
            hl = 0.1 * (1.25 if kh else 1.0) * (1.15 if self.s["species"] == "othari" else 1.0)
            hw = r[2] * 1.9
            hand = block("Hand", (wr[0], wr[1] - 0.005, wr[2] - hl / 2 - 0.01), (hw * 0.75, hw * 1.15, hl), (0, 0, 0), 0.8)
            self.add(done(hand, self.skin))
            th = spike("Thumb", (wr[0] - sx * hw * 0.2, wr[1] - hw * 0.45, wr[2] - 0.03), (wr[0] - sx * hw * 0.3, wr[1] - hw * 0.75, wr[2] - hl * 0.7), hw * 0.22)
            self.add(done(th, self.skin))
            if kh:
                for k in (-1, 0, 1):
                    cp = Vector((wr[0] + k * hw * 0.25, wr[1] - 0.02, wr[2] - hl - 0.01))
                    self.add(done(spike("Claw", cp + Vector((0, 0, 0.02)), cp + Vector((0, -0.02, -0.05)), 0.014), m(BONE, 0.5)))

    def skirt(self, outfit):
        sp = self.sp
        d = sp["depth"]
        prim = m(self.c("primary"))
        trim = metal(self.c("trim"))
        if outfit in ("toga", "robe", "stola"):
            hem_z = sp["ankle"] + 0.03
            secs = [(hem_z, ringN(14, sp["hip_w"] * 1.75, d * 1.95, 0.05), 0, 0.0),
                    ((hem_z + sp["hip"]) / 2, ringN(14, sp["hip_w"] * 1.42, d * 1.55, 0.04), 0, 0.0),
                    (sp["hip"], ringN(14, sp["hip_w"] * 1.18, d * 1.22, 0.02), 0, 0.0),
                    (sp["waist"] + 0.02, ringN(14, sp["waist_w"] * 1.14, d * 1.08, 0.0), 0, 0.0)]
            self.add(done(stack("Skirt", secs, cap_bottom=False, cap_top=False), prim))
            hem = stack("Hem", [(hem_z - 0.005, ringN(14, sp["hip_w"] * 1.78, d * 1.98, 0.05), 0, 0), (hem_z + 0.05, ringN(14, sp["hip_w"] * 1.73, d * 1.92, 0.05), 0, 0)],
                        cap_bottom=False, cap_top=False)
            self.add(done(hem, m(self.c("secondary")) if outfit == "toga" else trim))
        elif outfit == "tunic":
            hem_z = (sp["knee"] + sp["hip"]) / 2 - 0.04
            secs = [(hem_z, ringN(12, sp["hip_w"] * 1.45, d * 1.5, 0.05), 0, 0.0), (sp["hip"], ringN(12, sp["hip_w"] * 1.2, d * 1.25, 0.03), 0, 0.0),
                    (sp["waist"] + 0.02, ringN(12, sp["waist_w"] * 1.14, d * 1.08, 0.0), 0, 0.0)]
            self.add(done(stack("Skirt", secs, cap_bottom=False, cap_top=False), prim))
            hem = stack("Hem", [(hem_z - 0.005, ringN(12, sp["hip_w"] * 1.48, d * 1.53, 0.05), 0, 0), (hem_z + 0.04, ringN(12, sp["hip_w"] * 1.44, d * 1.49, 0.05), 0, 0)],
                        cap_bottom=False, cap_top=False)
            self.add(done(hem, trim))
        else:
            # military skirt: cloth under-skirt, leather strips, a tabard for the Kharad king
            hem_z = (sp["knee"] + sp["hip"]) / 2 - 0.02
            under = m(self.c("secondary"))
            secs = [(hem_z, ringN(12, sp["hip_w"] * 1.4, d * 1.45, 0.05), 0, 0.0), (sp["waist"] - 0.06, ringN(12, sp["waist_w"] * 1.2, d * 1.12, 0.0), 0, 0.0)]
            self.add(done(stack("Skirt", secs, cap_bottom=False, cap_top=False), under))
            n = 12
            for i in range(n):
                a = 2 * math.pi * (i + 0.5) / n
                x, y = math.cos(a) * sp["hip_w"] * 1.32, math.sin(a) * d * 1.4
                z0 = sp["waist"] - 0.08
                ln = (z0 - hem_z) * 0.75
                st = block("Pteryx", (x, y, z0 - ln / 2), (0.05, 0.012, ln), (0, 0, a + math.pi / 2))
                self.add(done(st, m(LEATHER)))
                self.add(done(block("PteryxTip", (x * 1.01, y * 1.01, z0 - ln), (0.052, 0.016, 0.02), (0, 0, a + math.pi / 2)), trim))
            belt = stack("Belt", [(sp["waist"] - 0.1, ring8(sp["waist_w"] * 1.24, d * 1.22, d * 1.15), 0, 0),
                                  (sp["waist"] - 0.04, ring8(sp["waist_w"] * 1.24, d * 1.22, d * 1.15), 0, 0)])
            self.add(done(belt, trim))
            if self.s["species"] == "kharad":
                tab = block("Tabard", (0, -d * 1.5, hem_z + 0.02), (0.2, 0.02, (sp["waist"] - hem_z) * 1.25), (0.08, 0, 0))
                self.add(done(tab, under))
                self.add(done(block("TabardTrim", (0, -d * 1.5 - 0.012, hem_z - (sp["waist"] - hem_z) * 0.6 + 0.02), (0.21, 0.02, 0.03), (0.08, 0, 0)), trim))

    def tail(self):
        sp = self.sp
        path = [(0, 0.12, sp["hip"]), (0, 0.38, sp["hip"] - 0.25), (0, 0.64, sp["hip"] - 0.6), (0, 0.84, 0.2), (0, 0.98, 0.07)]
        t = tube("Tail", path, [0.13, 0.1, 0.07, 0.04, 0.0], 6)
        self.add(done(t, self.skin))
        for (y, z, s) in ((0.36, sp["hip"] - 0.14, 0.05), (0.6, sp["hip"] - 0.5, 0.04), (0.8, 0.3, 0.03)):
            self.add(done(spike("Dorsal", (0, y, z), (0, y + s * 1.4, z + s * 1.2), s * 0.4), m(K.SKIN_DARK)))

    # ------------------------------------------------------------------ heads
    def head(self):
        sp = self.sp
        species = self.s["species"]
        z0 = sp["neck_top"]
        if species == "kharad":
            KH.Z0 = sp["neck_top"] + 0.02
            for o in KH.build_head(crown=self.s.get("headwear") == "kharad_crown", bust=False, skin_hex=self.s["skin"]):
                self.add(o)
            return
        s = sp["head"] * (0.94 if self.s.get("sex") == "f" else 1.0)
        fem = self.s.get("sex") == "f"
        skin = self.skin
        dark = m("2a1e1a", 0.5)
        hair = m(self.c("hair", "3a2a20"))
        if species == "veyari":
            secs = [(0.0, ring8(0.04, 0.07, 0.01), 0, -0.03), (0.06, ring8(0.062, 0.088, 0.06), 0, -0.01), (0.13, ring8(0.076, 0.098, 0.1), 0, 0.01),
                    (0.2, ring8(0.074, 0.088, 0.125), 0, 0.03), (0.26, ring8(0.06, 0.06, 0.13), 0, 0.055), (0.3, ring8(0.03, 0.03, 0.08), 0, 0.08)]
        elif species == "othari":
            secs = [(0.0, ring8(0.085, 0.09, 0.03), 0, -0.02), (0.06, ring8(0.11, 0.105, 0.08), 0, -0.01), (0.12, ring8(0.115, 0.11, 0.1), 0, 0.0),
                    (0.18, ring8(0.105, 0.1, 0.1), 0, 0.0), (0.24, ring8(0.08, 0.075, 0.085), 0, 0.0), (0.27, ring8(0.04, 0.04, 0.045), 0, 0.0)]
        else:
            jw = 0.88 if fem else 1.0
            secs = [(0.0, ring8(0.045 * jw, 0.075, 0.01), 0, -0.03), (0.05, ring8(0.07 * jw, 0.09, 0.06), 0, -0.01), (0.11, ring8(0.082, 0.1, 0.09), 0, 0.0),
                    (0.17, ring8(0.085, 0.095, 0.1), 0, 0.0), (0.23, ring8(0.07, 0.075, 0.085), 0, 0.0), (0.26, ring8(0.035, 0.04, 0.045), 0, 0.0)]
        secs = [(z0 + z * s, [(x * s, y * s) for (x, y) in pts], cx, cy * s) for (z, pts, cx, cy) in secs]
        self.add(done(stack("Head", secs), skin))
        H = lambda z: z0 + z * s  # noqa: E731
        front = lambda z: -0.1 * s  # noqa: E731
        # face: nose wedge, brow, eyes, mouth, ears
        nose_w = 0.024 * s * (1.5 if species == "othari" else 1.0)
        self.add(done(pyramid("Nose", [(-nose_w, -0.088 * s, H(0.085)), (nose_w, -0.088 * s, H(0.085)), (0, -0.092 * s, H(0.14))], (0, -0.12 * s, H(0.088))), skin))
        eye_col = m("ffc23a", 0.3, 0, "ffae00", 4.0) if species == "veyari" else (m("e89a3a", 0.4, 0, "e07a10", 1.5) if species == "othari" else dark)
        ey = H(0.128 if species != "othari" else 0.115)
        for sx in (1, -1):
            ex = sx * 0.036 * s
            ew = 0.022 * s if species != "veyari" else 0.03 * s
            self.add(done(mesh_from("Eye", [(ex - ew / 2, -0.093 * s, ey - 0.008 * s), (ex + ew / 2, -0.093 * s, ey - 0.008 * s), (ex + ew / 2, -0.093 * s, ey + 0.008 * s),
                                            (ex - ew / 2, -0.093 * s, ey + 0.008 * s)], [(0, 1, 2, 3)]), eye_col))
            if species == "othari":
                self.add(done(block("BrowPlate", (sx * 0.045 * s, -0.1 * s, H(0.15)), (0.075 * s, 0.035 * s, 0.035 * s), (0.25, 0, -sx * 0.15)), self.dark_skin()))
            else:
                self.add(done(block("Brow", (sx * 0.036 * s, -0.094 * s, ey + 0.022 * s), (0.034 * s, 0.012 * s, 0.009 * s), (0, 0, -sx * 0.12)), hair if species == "human" else self.dark_skin()))
            # ears
            if species == "veyari":
                ear = pyramid("Ear", [(sx * 0.072 * s, -0.01 * s, H(0.1)), (sx * 0.072 * s, 0.03 * s, H(0.1)), (sx * 0.074 * s, 0.01 * s, H(0.16))], (sx * 0.15 * s, 0.07 * s, H(0.22)))
            else:
                ex2 = 0.083 * s if species == "human" else 0.112 * s
                ear = pyramid("Ear", [(sx * ex2, -0.01 * s, H(0.09)), (sx * ex2, 0.03 * s, H(0.1)), (sx * ex2, 0.01 * s, H(0.15))], (sx * (ex2 + 0.018 * s), 0.02 * s, H(0.12)))
            self.add(done(ear, skin))
        self.add(done(block("Mouth", (0, -0.088 * s, H(0.058)), (0.036 * s, 0.006, 0.006)), m("6a3a30", 0.6)))
        if species == "veyari":
            # swept crest fins
            for sx in (1, -1):
                fin = mesh_from("Crest", [(sx * 0.03 * s, 0.0, H(0.26)), (sx * 0.035 * s, 0.1 * s, H(0.27)), (sx * 0.06 * s, 0.24 * s, H(0.36)), (sx * 0.05 * s, 0.07 * s, H(0.21))],
                                [(0, 1, 2), (0, 2, 3)])
                s2 = fin.modifiers.new("sol", "SOLIDIFY")
                s2.thickness = 0.012
                K.apply_all(fin)
                self.add(done(fin, hair))
        self.hair(secs, s, hair)
        self.beard(s, hair)

    def dark_skin(self):
        c = self.s["skin"]
        rgb = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
        return m("%02x%02x%02x" % tuple(int(v * 0.72) for v in rgb))

    def hair(self, secs, s, hair):
        style = self.s.get("hair_style", "short")
        sp = self.sp
        z0 = sp["neck_top"]
        H = lambda z: z0 + z * s  # noqa: E731
        species = self.s["species"]
        if style in ("bald", None) or self.s.get("headwear") == "helmet":
            return
        if species == "veyari":
            if style == "long":
                self.add(done(block("Hair", (0, 0.1 * s, H(0.1)), (0.13 * s, 0.05 * s, 0.24 * s), (-0.25, 0, 0), 0.9), hair))
            return
        # a faceted cap that sits over the crown and the back of the head, clear of the face
        lo = 0.16 if style != "cropped" else 0.18
        cap = []
        for (z, pts, cx, cy) in secs:
            if z >= H(lo) - 1e-6:
                cap.append((z + 0.006, [(x * 1.12, (y * 1.08 if y < 0 else y * 1.14)) for (x, y) in pts], cx, cy + 0.004))
        cap.insert(0, (H(lo), [(x * 1.12 * s / s, (y * 1.06 if y < 0 else y * 1.14)) for (x, y) in ring8(0.086 * s, 0.098 * s, 0.1 * s)], 0, 0.004))
        self.add(done(stack("HairCap", cap), hair))
        back = block("HairBack", (0, 0.085 * s, H(0.13)), (0.15 * s, 0.035 * s, 0.13 * s), (0.12, 0, 0), 1.05)
        self.add(done(back, hair))
        if style == "curly":
            for i in range(7):
                a = -math.pi / 2 + (i - 3) * 0.45
                p = (math.cos(a) * 0.08 * s, math.sin(a) * 0.09 * s + 0.01, H(0.22))
                self.add(done(pyramid("Curl", [(p[0] - 0.02, p[1] - 0.015, p[2]), (p[0] + 0.02, p[1] - 0.015, p[2]), (p[0], p[1] + 0.02, p[2])], (p[0] * 1.1, p[1] * 1.1, p[2] + 0.04)), hair))
        elif style == "bun":
            self.add(done(block("Bun", (0, 0.11 * s, H(0.2)), (0.07 * s, 0.06 * s, 0.07 * s), (0.3, 0, 0), 0.7), hair))
        elif style == "long":
            self.add(done(block("Long", (0, 0.095 * s, H(0.0)), (0.16 * s, 0.035 * s, 0.25 * s), (-0.1, 0, 0), 1.1), hair))
        elif style == "braids":
            for sx in (1, -1):
                self.add(done(tube("Braid", [(sx * 0.06 * s, 0.07 * s, H(0.12)), (sx * 0.07 * s, 0.08 * s, H(-0.12))], [0.025 * s, 0.018 * s], 4), hair))

    def beard(self, s, hair):
        style = self.s.get("beard", "none")
        sp = self.sp
        z0 = sp["neck_top"]
        H = lambda z: z0 + z * s  # noqa: E731
        if style == "plates":
            for i, x in enumerate((-0.05, 0.0, 0.05)):
                ln = 0.13 if i == 1 else 0.1
                self.add(done(block("JawPlate", (x * s, -0.09 * s, H(0.03) - ln / 2 + 0.02), (0.04 * s, 0.03 * s, ln), (0.1, 0, 0), 0.85), hair))
                self.add(done(block("Bead", (x * s, -0.094 * s, H(0.03) - ln + 0.035), (0.045 * s, 0.035 * s, 0.018), (0.1, 0, 0)), metal(GOLD)))
            return
        if style not in ("short", "full"):
            return
        drop = 0.0 if style == "short" else 0.06
        secs = [(H(-0.02) - drop, 0.05 * s, 0.075 * s, 0, -0.025 * s), (H(0.05), 0.078 * s, 0.098 * s, 0, -0.008 * s), (H(0.1), 0.088 * s, 0.104 * s, 0, 0.0)]
        b = shell("Beard", secs, math.radians(-90 - 105), math.radians(-90 + 105), 0.012, 10)
        self.add(done(b, hair))
        self.add(done(block("Moustache", (0, -0.098 * s, H(0.072)), (0.06 * s, 0.014 * s, 0.014 * s)), hair))

    # ------------------------------------------------------------------ headwear, cloak, props
    def headwear(self):
        hw = self.s.get("headwear") or "none"
        if hw in ("none", "kharad_crown"):
            return
        sp = self.sp
        s = sp["head"]
        z0 = sp["neck_top"]
        H = lambda z: z0 + z * s  # noqa: E731
        species = self.s["species"]
        cy = 0.04 * s if species == "veyari" else 0.0
        zb = H(0.19 if species != "veyari" else 0.2)
        rx, ry = 0.096 * s, 0.108 * s
        if species == "othari":
            rx, ry, zb = 0.12 * s, 0.112 * s, H(0.18)
        if hw == "helmet":
            met = metal(self.c("primary") if self.s["outfit"] in ("armour", "scale") else "aeb4bc")
            secs = [(H(0.1), ring8(rx * 1.12, ry * 1.08, ry * 1.12), 0, 0), (H(0.2), ring8(rx * 1.1, ry * 1.06, ry * 1.1), 0, 0),
                    (H(0.27), ring8(rx * 0.8, ry * 0.75, ry * 0.8), 0, 0), (H(0.3), ring8(rx * 0.3, ry * 0.3, ry * 0.3), 0, 0)]
            self.add(done(stack("Helmet", secs, cap_bottom=False), met))
            self.add(done(block("Brim", (0, -ry * 1.05, H(0.18)), (rx * 1.6, 0.03, 0.025)), metal(self.c("trim"))))
            for sx in (1, -1):
                self.add(done(block("Cheek", (sx * rx * 1.02, -0.03 * s, H(0.07)), (0.012, 0.07 * s, 0.1 * s), (0, 0, sx * 0.1)), met))
            crest = mesh_from("Crest", [(0, -ry * 0.9, H(0.29)), (0, ry * 1.1, H(0.27)), (0, ry * 1.2, H(0.4)), (0, 0, H(0.45)), (0, -ry * 1.0, H(0.4))],
                              [(0, 1, 2, 3, 4)], tri_nonplanar=False)
            sol = crest.modifiers.new("sol", "SOLIDIFY")
            sol.thickness = 0.05
            K.apply_all(crest)
            self.add(done(crest, m(self.c("secondary"))))
            return
        if hw.startswith("laurel"):
            col = metal(GOLD) if hw == "laurel_gold" else m("4f7a3a")
            for sx in (1, -1):
                for i in range(7):
                    a = -math.pi / 2 + sx * (0.35 + i * 0.36)
                    p = Vector((math.cos(a) * rx * 1.02, cy + math.sin(a) * ry * 1.02, zb - 0.01 + 0.008 * (i % 2)))
                    out = Vector((math.cos(a), math.sin(a), 0))
                    tang = Vector((-math.sin(a), math.cos(a), 0)) * -sx
                    leaf = [p - tang * 0.026, p + out * 0.026, p + tang * 0.045 + Vector((0, 0, 0.036)), p - out * 0.008]
                    self.add(done(mesh_from("Leaf", [tuple(v) for v in leaf], [(0, 1, 2), (0, 2, 3)], False), col))
            return
        cols = {"crown_gold": GOLD, "crown_silver": SILVER, "crown_iron": IRON, "diadem": GOLD, "diadem_silver": SILVER, "circlet": SILVER, "circlet_gold": GOLD}
        met = metal(cols.get(hw, GOLD))
        n = 8
        tall = 0.035 if hw.startswith("crown") else 0.018
        band = stack("Band", [(zb - 0.012, ringN(n, rx * 1.03, ry * 1.03, 0, -math.pi / 2), 0, cy), (zb + tall, ringN(n, rx * 1.07, ry * 1.07, 0, -math.pi / 2), 0, cy)],
                     cap_bottom=False, cap_top=False)
        self.add(done(band, met))
        if hw.startswith("crown"):
            for i in range(n):
                a = -math.pi / 2 + 2 * math.pi * i / n
                p = Vector((math.cos(a) * rx * 1.07, cy + math.sin(a) * ry * 1.07, zb + tall))
                out = Vector((math.cos(a), math.sin(a), 0))
                tang = Vector((-math.sin(a), math.cos(a), 0))
                h = 0.06 if i == 0 else 0.04
                self.add(done(pyramid("Point", [tuple(p - tang * 0.022), tuple(p + tang * 0.022), tuple(p - out * 0.012)], tuple(p + Vector((0, 0, h)) + out * 0.006)), met))
        if hw.startswith("diadem") or hw.startswith("crown"):
            gem = m("b31d2a", 0.2, 0, "5a0a10", 0.6) if hw != "diadem_silver" else m("3f8fd0", 0.2, 0, "10406a", 0.6)
            gp = Vector((0, cy - ry * 1.09, zb + tall * 0.5))
            self.add(done(mesh_from("Gem", [tuple(gp + Vector((0, -0.01, 0.02))), tuple(gp + Vector((0.014, 0, 0))), tuple(gp + Vector((0, -0.01, -0.016))), tuple(gp + Vector((-0.014, 0, 0)))],
                                    [(0, 3, 2, 1)], False), gem))
            if hw.startswith("diadem"):
                self.add(done(pyramid("DiademPeak", [tuple(gp + Vector((-0.03, 0.006, 0.0))), tuple(gp + Vector((0.03, 0.006, 0.0))), tuple(gp + Vector((0, 0.012, 0.0)))],
                                      tuple(gp + Vector((0, 0.0, 0.05)))), met))

    def cloak(self):
        sp = self.sp
        d = sp["depth"]
        col = m(self.c("cloak"))
        lining = m(self.s.get("lining") or self.dark(self.c("cloak")))
        trim = metal(self.c("trim"))
        top = sp["shoulder"] + 0.03
        bottom = sp["ankle"] + (0.12 if self.s["species"] != "kharad" else -0.1)
        W = sp["sh_w"]
        secs = [(top, W * 0.95, d * 1.35, 0, 0.02), (top - 0.25, W * 1.18, d * 1.75, 0, 0.06), ((top + bottom) / 2, W * 1.38, d * 2.1, 0, 0.1),
                (bottom, W * 1.6, d * 2.4, 0, 0.13)]
        secs.reverse()
        a0, a1 = math.radians(-25), math.radians(205)
        cl = shell("Cloak", secs, a0, a1, 0.025, 12)
        done(cl, col, lambda c, n: 1 if Vector((n.x, n.y, 0)).dot(Vector((c.x - self.ox, c.y - 0.05, 0)).normalized()) < -0.2 else 0, [lining])
        self.add(cl)
        hem = shell("CloakHem", [(bottom - 0.005, W * 1.61, d * 2.41, 0, 0.13), (bottom + 0.05, W * 1.585, d * 2.37, 0, 0.128)], a0, a1, 0.03, 12)
        self.add(done(hem, trim))
        # mantle over the shoulders, open at the front
        man = shell("Mantle", [(sp["shoulder"] - 0.08, W * 1.25, d * 1.5, 0, 0.01), (sp["shoulder"] + 0.04, W * 1.0, d * 1.18, 0, 0.0),
                               (sp["neck"] + 0.03, W * 0.5, d * 0.75, 0, 0.0)], math.radians(-90 + 34), math.radians(270 - 34), 0.03, 14)
        self.add(done(man, col))
        for sx in (1, -1):
            disc = tube("Clasp", [(sx * W * 0.62, -d * 1.3, sp["shoulder"] - 0.04), (sx * W * 0.62, -d * 1.42, sp["shoulder"] - 0.04)], [0.04, 0.04], 8)
            self.add(done(disc, trim))

    def dark(self, hexcol, k=0.6):
        rgb = [int(hexcol[i:i + 2], 16) for i in (0, 2, 4)]
        return "%02x%02x%02x" % tuple(int(v * k) for v in rgb)

    def props(self):
        sp = self.sp
        p = self.s.get("prop") or "none"
        hand = Vector((-(sp["arm_x"] + 0.09), -0.03, sp["hip"] - 0.06))     # the character's right hand (-X)
        lhand = Vector(((sp["arm_x"] + 0.09), -0.03, sp["hip"] - 0.06))
        if p in ("staff", "staff_gold", "spear"):
            ln = 2.1 if p == "spear" else 1.8
            col = metal(GOLD) if p == "staff_gold" else m("6b4a2e")
            base = hand + Vector((-0.02, -0.04, -0.85))
            self.add(done(tube("Shaft", [tuple(base), tuple(base + Vector((0, 0, ln)))], [0.02, 0.018], 6), col))
            top = base + Vector((0, 0, ln))
            if p == "spear":
                self.add(done(pyramid("Blade", [tuple(top + Vector((-0.035, 0, 0))), tuple(top + Vector((0, -0.012, 0))), tuple(top + Vector((0.035, 0, 0))),
                                                tuple(top + Vector((0, 0.012, 0)))], tuple(top + Vector((0, 0, 0.22)))), metal(SILVER)))
            else:
                self.add(done(block("Finial", tuple(top + Vector((0, 0, 0.04))), (0.07, 0.07, 0.07), (0.6, 0.6, 0)), metal(GOLD)))
                if p == "staff_gold":
                    for k in range(6):
                        a = 2 * math.pi * k / 6
                        self.add(done(spike("Ray", tuple(top + Vector((0, 0, 0.04))), tuple(top + Vector((math.cos(a) * 0.12, 0, 0.04 + math.sin(a) * 0.12))), 0.012), metal(GOLD)))
        elif p == "sword":
            hip = Vector((sp["hip_w"] * 1.25, -0.02, sp["hip"] - 0.02))
            self.add(done(block("Scabbard", tuple(hip + Vector((0.02, 0.0, -0.18))), (0.05, 0.03, 0.4), (0, 0.18, 0), 0.8), m("3d2a1e")))
            self.add(done(block("Guard", tuple(hip + Vector((-0.02, 0, 0.05))), (0.11, 0.03, 0.025), (0, 0.18, 0)), metal(GOLD)))
            self.add(done(block("Grip", tuple(hip + Vector((-0.03, 0, 0.11))), (0.03, 0.03, 0.1), (0, 0.18, 0)), m(LEATHER)))
        elif p == "scroll":
            self.add(done(tube("Scroll", [tuple(hand + Vector((0.06, -0.03, 0.0))), tuple(hand + Vector((-0.06, -0.03, 0.0)))], [0.03, 0.03], 6), m("e6d9b8")))
        elif p == "tablet":
            self.add(done(block("Tablet", tuple(lhand + Vector((0.0, -0.06, 0.08))), (0.03, 0.2, 0.15), (0.2, 0, 0)), m("6b4a2e")))
        if self.s.get("shield"):
            c = lhand + Vector((0.07, -0.04, 0.2))
            secs = []
            for z, k in ((-0.38, 0.95), (-0.15, 1.0), (0.15, 1.0), (0.38, 0.95)):
                secs.append((c.z + z, 0.3 * k, 0.2, c.x + 0.16, c.y))
            sh = shell("Shield", secs, math.radians(155), math.radians(205), 0.03, 6)
            self.add(done(sh, m(self.c("shield"))))
            self.add(done(block("Boss", (c.x - 0.13, c.y, c.z), (0.05, 0.09, 0.09), (0, 0, 0)), metal(GOLD)))


# ----------------------------------------------------------------------------- rendering
def lineup(ids, path, samples, spacing=1.15):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    allp = []
    x0 = -spacing * (len(ids) - 1) / 2
    for i, cid in enumerate(ids):
        allp += Figure(cid, CAST[cid], x0 + i * spacing).build()
    K.stage(samples)
    w = spacing * len(ids)
    sc = bpy.context.scene
    dist = max(5.0, w * 1.12 + 1.5)
    K.shoot(path, (w * 0.1, -dist, 1.7), (0, 0, 1.05), 45, (max(1400, int(360 * len(ids))), 1000))
    return path


def single(cid, out, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = Figure(cid, CAST[cid]).build()
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    os.makedirs(os.path.join(ROOT, "assets", "characters"), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "assets", "characters", cid + ".glb"), use_selection=True, export_format="GLB")
    if samples <= 0:
        return tris, []
    K.stage(samples)
    h = SPECIES[CAST[cid]["species"]]["neck_top"] + 0.3
    files = []
    for k, yaw in (("front", -25), ("side", -90), ("back", 155)):
        f = os.path.join(out, "cast_%s_%s.png" % (cid, k))
        K.shoot(f, K.orbit((0, 0, h * 0.5), h * 2.3, yaw, 6), (0, 0, h * 0.5), 50, (600, 900))
        files.append(f)
    return tris, files


def compose(files, out, labels=None):
    from PIL import Image, ImageDraw
    ims = [Image.open(f).convert("RGBA") for f in files]
    W = sum(i.width for i in ims)
    H = max(i.height for i in ims)
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(148 - 36 * t), int(94 - 26 * t), int(78 - 20 * t)))
    x = 0
    for im in ims:
        bg.paste(im, (x, 0), im)
        x += im.width
    bg.save(out)
    print("sheet", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--turn", action="store_true", help="also render front/side/back of each character")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    out = os.path.join(ROOT, "renders")
    os.makedirs(out, exist_ok=True)
    ids = args.only.split(",") if args.only else list(CAST)
    for cid in ids:
        tris, files = single(cid, out, args.samples if args.turn and not args.no_render else 0)
        print("built", cid, tris, "triangles")
        if files:
            compose(files, os.path.join(out, "cast_%s.png" % cid))
    if args.no_render:
        return
    if args.only:
        p = lineup(ids, os.path.join(out, "cast_selection.png"), args.samples)
        compose([p], p)
        return
    for g, _ in GROUPS:
        gid = [c for c in CAST if CAST[c]["group"] == g]
        p = lineup(gid, os.path.join(out, "cast_%s.png" % g), args.samples)
        compose([p], p)


if __name__ == "__main__":
    main()
