"""Stage 9: lighting and atmosphere - sun + world gradient, sun disc, low distant hills, large angular
polygonal clouds (convex hulls with per-facet sunset shading), and view-distance haze in every material."""
import math
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

import rc_common as R
import city as T
from city import Acc
import vista as V
import kharad as K

SUN = V.SUN
MOUNTAIN_MATS = set()


def mountains(rng):
    """Low, soft ranges at 10-13 km so the city reads to the horizon (heights kept modest)."""
    m = Acc("Mountains")
    for i in range(30):
        t = rng.uniform(-1.05, 1.05)
        if abs(t + 0.4) < 0.12:          # keep the sun's horizon clear
            continue
        r = rng.uniform(10000, 13500)
        c = Vector((math.sin(-t) * r, -math.cos(t) * r, 0))
        h = rng.uniform(150, 300) * (1.0 if abs(t) > 0.3 else 0.7)
        rx, ry = rng.uniform(1500, 2600), rng.uniform(700, 1300)
        col = T.rgbhex([a + (b - a) * rng.uniform(0.0, 0.35) for a, b in zip(T.hexrgb("8a76b0"), T.hexrgb("b094b4"))])
        pts = [(c.x + math.cos(2 * math.pi * k / 7 + rng.uniform(-0.2, 0.2)) * rx, c.y + math.sin(2 * math.pi * k / 7) * ry, R.CITY - 5) for k in range(7)]
        peak = (c.x + rng.uniform(-150, 150), c.y + rng.uniform(-150, 150), R.CITY + 60 + h)
        mid = [((p[0] * 0.55 + peak[0] * 0.45), (p[1] * 0.55 + peak[1] * 0.45), R.CITY + 60 + h * rng.uniform(0.35, 0.55)) for p in pts]
        k1, k2 = m.key(col, 0.95), m.key(T.rgbhex([v * 1.06 for v in T.hexrgb(col)]), 0.95)
        for k in range(7):
            j = (k + 1) % 7
            m.poly([pts[k], pts[j], mid[j], mid[k]], k1)
            m.poly([mid[k], mid[j], peak], k2)
    o = m.build()
    MOUNTAIN_MATS.update(ms.name for ms in o.data.materials)
    return o


def hull(points):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    tris = []
    for f in bm.faces:
        tris.append([v.co.copy() for v in f.verts])
    bm.free()
    return tris


def clouds(rng):
    """Large angular cloud banks: wide faceted relief sheets facing the viewer, with a flat-ish base and a
    jagged crest. Upper facets catch the sun (gold/peach), lower ones fall to rose and lavender."""
    cl = Acc("Clouds")
    gold, peach, coral, rose, lav = (cl.key("ffd88e", 0.9, 0, "ffcf80", 1.9), cl.key("fdbd80", 0.9, 0, "f8b072", 1.5), cl.key("f2a08a", 0.9, 0, "ea9484", 1.2),
                                      cl.key("d898aa", 0.9, 0, "cc8ca4", 1.0), cl.key("aa8ebc", 0.9, 0, "9c84b4", 0.9))
    # (bearing, elevation deg, length m, height m): heavy banks upper-left, lighter wisps upper-right
    banks = [(0.50, 11.5, 1700, 260), (0.30, 15.0, 1100, 180), (0.72, 7.5, 900, 150), (0.12, 9.0, 700, 110),
             (-0.60, 10.5, 1200, 190), (-0.78, 14.5, 900, 150), (-0.42, 6.5, 700, 90), (-0.95, 8.0, 800, 120), (0.95, 13.0, 800, 160)]
    for (t, elev, L, H) in banks:
        d = rng.uniform(2900, 3300)
        c = Vector((math.sin(-t) * d, -math.cos(t) * d, R.CAM_LOC[2] + d * math.tan(math.radians(elev))))
        fwd = (c - Vector(R.CAM_LOC)).normalized()
        u = Vector((-fwd.y, fwd.x, 0)).normalized()
        w = Vector((0, 0, 1))
        tilt = rng.uniform(-0.12, 0.12)            # banks lean slightly, as in the reference
        n = max(6, int(L / 110))
        cols = []
        for i in range(n + 1):
            x = (i / n - 0.5) * L
            prof = math.sin(math.pi * i / n) ** 0.7
            base = rng.uniform(-0.08, 0.05) * H + x * tilt
            top = base + H * prof * rng.uniform(0.55, 1.15)
            mid = base + (top - base) * rng.uniform(0.35, 0.6)
            lip = base - H * 0.12 * prof * rng.random()
            dz = lambda k: -fwd * (k * H * 0.6)            # relief toward the viewer
            cols.append([c + u * (x + rng.uniform(-20, 20)) + w * lip,
                         c + u * x + w * mid + dz(rng.uniform(0.3, 0.8)),
                         c + u * (x + rng.uniform(-30, 30) - H * 0.5) + w * top])
        for i in range(n):
            A, B = cols[i], cols[i + 1]
            for r, keys in ((0, (lav, rose)), (1, (coral, gold if i < n * 0.6 else peach))):
                p00, p01, p10, p11 = A[r], A[r + 1], B[r], B[r + 1]
                tris = ((p00, p10, p11), (p00, p11, p01)) if (i + r) % 2 else ((p00, p10, p01), (p10, p11, p01))
                for k, tri in enumerate(tris):
                    key = keys[k]
                    if r == 1 and rng.random() < 0.25:
                        key = peach
                    nrm = (tri[1] - tri[0]).cross(tri[2] - tri[0])
                    pts = [tuple(p) for p in tri]
                    cl.poly(pts if nrm.dot(fwd) < 0 else pts[::-1], key)
    return cl.build()


def sun_disc():
    s = Acc("Sun")
    sc = Vector(R.CAM_LOC) + SUN * 6000
    u = SUN.cross(Vector((0, 0, 1))).normalized()
    v = u.cross(SUN).normalized()
    for rad, key in ((52, s.key("fff2c8", 0.5, 0, "fff0b0", 40.0)), (95, s.key("ffd080", 0.5, 0, "ffc070", 6.0)), (240, s.key("ffa86a", 0.5, 0, "ffa068", 1.4))):
        s.poly([tuple(sc - SUN * rad * 0.02 + (u * math.cos(2 * math.pi * q / 20) + v * math.sin(2 * math.pi * q / 20)) * rad) for q in range(20)], key)
    return s.build()


def build_atmosphere(samples=32, seed=5):
    R.clear("Lighting & Atmosphere")
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)
    rng = random.Random(seed)
    before = set(bpy.data.objects)
    objs = [mountains(rng), clouds(rng), sun_disc()]
    for o in objs:
        o.visible_shadow = False
    V.lighting(samples)
    for o in set(bpy.data.objects) - before:
        R.move_to(o, "Lighting & Atmosphere")


def apply_haze():
    """Aerial perspective: blend every opaque material toward the haze colour with view distance."""
    hp = R.PARAMS["haze"]
    hz = K.hexc(hp["colour"])
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.name in MOUNTAIN_MATS or mat.get("hazed"):
            continue
        nt = mat.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if out is None or bsdf is None or bsdf.inputs["Emission Strength"].default_value > 0.5:
            continue
        cam = nt.nodes.new("ShaderNodeCameraData")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = hp["start_m"]
        mr.inputs["From Max"].default_value = hp["end_m"]
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 0.85
        cl = nt.nodes.new("ShaderNodeMath")
        cl.operation = "MULTIPLY"
        cl.inputs[1].default_value = hp["max"]
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = hz
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], pw.inputs[0])
        nt.links.new(pw.outputs["Value"], cl.inputs[0])
        nt.links.new(cl.outputs["Value"], mix.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(em.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        mat["hazed"] = True


def camera(res):
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        cd = bpy.data.cameras.new("Camera")
        cam = bpy.data.objects.new("Camera", cd)
        R.coll("Lighting & Atmosphere").objects.link(cam)
        sc.camera = cam
    cam.location = R.CAM_LOC
    cam.rotation_euler = (math.pi / 2 + math.radians(R.CAM_PITCH_DEG), 0.0, math.pi)
    cam.data.lens = R.CAM_LENS
    cam.data.clip_end = 20000.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    return cam
