"""Stage 5/6: procedural city layout and instancing.

The layout is intentional but irregular:
  - a street network (wandering avenues radiating from the forum, broken ring roads, hundreds of
    winding alleys) rasterised into a 4 m mask;
  - public squares with fountains and monuments;
  - neighbourhoods whose building mix depends on the district (public quarter around the forum,
    dense residential quarters, sparser outskirts) and on distance (detailed / mid / far assets);
  - lots packed into the gaps with an occupancy mask, at district-drifting orientations, each a
    linked duplicate of a library asset with its own footprint and height scale, set on the terrain;
  - the landmark temple integrated on its low hill inside a colonnaded precinct.
Parameters come from city_params.json; the random seed makes the city reproducible.
"""
import math
import random

import bpy
from mathutils import Matrix, Vector

import rc_common as R
import city as T
from city import Acc, ring

P = R.PARAMS
STATS = {}


def inst(entry, x, y, yaw, sxy=1.0, sz=1.0, cname="Residential", tag=""):
    o = bpy.data.objects.new("%s_%s" % (tag or entry["obj"].name.replace("ASSET_", ""), STATS.get("n", 0)), entry["mesh"])
    STATS["n"] = STATS.get("n", 0) + 1
    w, d = entry["dims"]
    c, s = math.cos(yaw), math.sin(yaw)
    zs = [R.terrain_z(x + c * u - s * v, y + s * u + c * v) for u in (-w / 2 * sxy, w / 2 * sxy) for v in (-d / 2 * sxy, d / 2 * sxy)]
    o.location = (x, y, min(zs) - 0.25)
    o.rotation_euler = (0, 0, yaw)
    o.scale = (sxy, sxy, sz)
    R.coll(cname).objects.link(o)
    return o


def landmark(lib, rng, LT, scale=1.0):
    """The capital's great temple: a large peripteral temple on a two-tier precinct podium on its low hill,
    framed by smaller temples, honorary columns, banners and cypresses. Short central steps only."""
    a = Acc("LandmarkTemple")
    z = R.terrain_z(LT.x, LT.y) - 2.0
    a.T = Matrix.Translation((LT.x, LT.y, z)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Scale(scale, 4)
    m, m2, g, cr = a.key(T.MARBLE), a.key(T.MARBLE2), a.key(T.GOLD, 0.5, 0.4), a.key(T.CRIMSON)
    tiers = [(118, 112, 7.0), (84, 92, 6.0)]
    zz = 0.0
    for (w, d, h) in tiers:
        a.box((0, 0, zz + h / 2), (w, d, h), m2)
        a.box((0, 0, zz + h - 0.2), (w + 1.2, d + 1.2, 0.5), m)
        a.box((0, 0, zz + h - 0.8), (w + 0.4, d + 0.4, 0.3), g)
        for k in range(8):       # short central flight on the camera side (local -Y after the pi turn)
            a.box((0, -d / 2 - 0.6 - (8 - k) * 0.7, zz + h * (k + 1) / 16), (16, 0.7, h * (k + 1) / 8), m)
        for sx in (-1, 1):       # banners down the podium face either side of the steps
            for q in (0.22, 0.36):
                T.banner_flat(a, (sx * w * q, -d / 2 - 0.15, zz + h - 0.9), 3.0, h * 0.75, 0.0)
        zz += h
    sub = a.T
    a.T = sub @ Matrix.Translation((0, 6, zz))
    T.temple(a, 46, 62, 20, rng, True, True)
    for sx in (-1, 1):
        a.T = sub @ Matrix.Translation((sx * 47, -22, tiers[0][2]))
        T.temple(a, 14, 20, 8, rng, False)
        a.T = sub @ Matrix.Identity(4)
        for k in range(3):
            x, y = sx * (30 + k * 4), -44 + k * 3
            a.stack([(zz, ring(10, 1.1, 1.1), x, y), (zz + 14, ring(10, 0.9, 0.9), x, y)], m)
            a.box((x, y, zz + 14.4), (2.4, 2.4, 0.8), g)
    a.T = Matrix.Identity(4)
    R.move_to(a.build(), "Temples & Monuments")
    for k in range(26):
        ang = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(48, 64)
        inst(lib["tree"][k % 2], LT.x + math.cos(ang) * rr, LT.y + math.sin(ang) * rr * 0.95, 0, rng.uniform(1.0, 1.5), rng.uniform(1.1, 1.6), "Vegetation", "Tree")


def build_city(lib, greybox=False):
    for c in ("Residential", "Public Buildings", "Temples & Monuments", "Towers & Arches", "Vegetation", "Streets & Plazas"):
        R.clear(c)
    STATS.clear()
    rng = random.Random(P["seed"])
    half = math.radians(P["view_half_angle_deg"])
    FORUM = Vector((P["forum"]["x"], P["forum"]["y"]))
    LT = Vector((P["landmark_temple"]["x"], P["landmark_temple"]["y"]))
    CELL = 4.0
    road, occ = set(), set()
    streets = Acc("Streets")

    def cells(x, y, r):
        r = int(r / CELL)
        cx, cy = int(math.floor(x / CELL)), int(math.floor(y / CELL))
        return [(cx + i, cy + j) for i in range(-r, r + 1) for j in range(-r, r + 1)]

    def paint(p0, p1, w, pave=False):
        p0, p1 = Vector(p0), Vector(p1)
        n = max(1, int((p1 - p0).length / (CELL * 0.7)))
        for k in range(n + 1):
            p = p0.lerp(p1, k / n)
            for c in cells(p.x, p.y, w / 2):
                road.add(c)
        if pave and (p1 - p0).length > 0.1:
            dv = (p1 - p0)
            nv = Vector((-dv.y, dv.x)).normalized() * (w / 2)
            z0, z1 = R.terrain_z(p0.x, p0.y) + 0.3, R.terrain_z(p1.x, p1.y) + 0.3
            streets.poly([(p0.x + nv.x, p0.y + nv.y, z0), (p0.x - nv.x, p0.y - nv.y, z0), (p1.x - nv.x, p1.y - nv.y, z1), (p1.x + nv.x, p1.y + nv.y, z1)],
                         streets.key("b39878", 0.95))

    def wander(start, heading, length, step, jitter, w, pave):
        p, h, dd = Vector(start), heading, 0.0
        while dd < length:
            h += rng.uniform(-jitter, jitter)
            q = p + Vector((math.sin(h), -math.cos(h))) * step
            paint(p, q, w, pave)
            p, dd = q, dd + step

    sw = P["street_width"]
    for ang in (-84, -62, -38, -20, 14, 36, 58, 78):
        wander(FORUM, math.radians(-ang + rng.uniform(-4, 4)), P["footprint_m"], 60, 0.05, sw["avenue"], True)
    for Rr in (150, 330, 560, 880, 1300, 1900, 2700, 3800, 5200):
        n = int(Rr * 2 * math.pi / 50)
        prev = None
        a0 = rng.uniform(-0.3, 0.3)
        for k in range(n + 1):
            if rng.random() < 0.09:
                prev = None
                continue
            t = a0 + 2 * math.pi * k / n
            rr = Rr * (1 + 0.06 * math.sin(3 * t + Rr)) + rng.uniform(-6, 6)
            p = Vector((FORUM.x + math.sin(t) * rr, FORUM.y - math.cos(t) * rr))
            if prev is not None and p.y < -60:
                paint(prev, p, sw["ring"], Rr < 2000)
            prev = p
    for _ in range(P["alleys"]):
        d0 = rng.uniform(80, 5000)
        th = rng.uniform(-half, half)
        wander((-math.sin(th) * d0, -math.cos(th) * d0), rng.uniform(0, 2 * math.pi), rng.uniform(80, 280), 28, 0.4, sw["alley"], d0 < 1000)
    stair_foot = LT + Vector((0, 70))

    # public squares: the forum and smaller piazzas, each with a fountain or monument
    squares = [(FORUM, 36, 30)]
    for _ in range(P["squares"]):
        d0 = rng.uniform(260, 2400)
        th = rng.uniform(-half * 0.85, half * 0.85)
        squares.append((Vector((-math.sin(th) * d0, -math.cos(th) * d0)), rng.uniform(14, 26), rng.uniform(12, 22)))
    for (c, w, d) in squares:
        for cc in cells(c.x, c.y, max(w, d) + 4):
            road.add(cc)
        z = R.terrain_z(c.x, c.y) + 0.32
        yaw = rng.uniform(-0.3, 0.3)
        R_ = Matrix.Rotation(yaw, 3, "Z")
        pts = [tuple(c.to_3d() + R_ @ Vector((u * w, v * d, 0)) + Vector((0, 0, z))) for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        streets.poly(pts, streets.key("c4ad8c", 0.95))
    if not greybox:
        mons = lib["monument"]
        for i, (c, w, d) in enumerate(squares[1:]):
            inst(mons[i % len(mons)], c.x, c.y, rng.uniform(0, 6.28), 1.0, 1.0, "Temples & Monuments", "Monument")
            for k in range(6):
                ang = 2 * math.pi * k / 6 + rng.uniform(-0.2, 0.2)
                inst(rng.choice(lib["tree"]), c.x + math.cos(ang) * w * 0.85, c.y + math.sin(ang) * d * 0.85, 0, rng.uniform(0.8, 1.2), rng.uniform(0.85, 1.2), "Vegetation", "Tree")

    def free(x, y, r):
        if abs(x - LT.x) < 60 * P["landmark_temple"]["scale"] + r and abs(y - LT.y) < 64 * P["landmark_temple"]["scale"] + r:
            return False
        for (lx, ly, lw, ld) in ((-118, -205, 44, 26), (-160, -270, 38, 24), (52, -240, 40, 24), (-82, -150, 30, 20)):
            if abs(x - lx) < lw / 2 + 8 + r and abs(y - ly) < ld / 2 + 12 + r:
                return False
        return y < -62 and abs(math.atan2(-x, -y)) < half

    def fits(x, y, w, d):
        for c in cells(x, y, max(w, d) / 2 * 0.8):
            if c in road or c in occ:
                return False
        return True

    def district_yaw(x, y):
        return 0.32 * math.sin(x / 260.0 + 1.3) + 0.26 * math.cos(y / 310.0) + 0.12 * math.sin((x + y) / 140.0)

    def choose(dist, x, y):
        if greybox:
            return "far", "Residential"
        if dist > P["mid_limit_m"]:
            return ("skyline" if rng.random() < 0.008 else "far"), ("Temples & Monuments" if False else "Residential")
        if dist > P["near_limit_m"]:
            r = rng.random()
            if r < 0.02:
                return "temple", "Temples & Monuments"
            if r < 0.026:
                return "tower", "Towers & Arches"
            if r < 0.055:
                return "public", "Public Buildings"
            return "mid", "Residential"
        mix = dict(P["mix_near"])
        near_forum = (Vector((x, y)) - FORUM).length < 260
        if near_forum:
            mix["public"] *= 3
            mix["temple"] *= 2.5
            mix["monument"] *= 2
        r = rng.random() * sum(mix.values())
        for k, v in mix.items():
            r -= v
            if r <= 0:
                cname = {"small": "Residential", "medium": "Residential", "large": "Residential", "public": "Public Buildings", "temple": "Temples & Monuments",
                         "tower": "Towers & Arches", "garden": "Vegetation", "monument": "Temples & Monuments"}[k]
                return k, cname
        return "medium", "Residential"

    hs = P["height_scale"]
    fs = P["footprint_scale"]
    built = 0
    for _ in range(P["lot_attempts"]):
        dist = 70 + (rng.random() ** 1.7) * (P["footprint_m"] - 70)
        th = rng.uniform(-half, half)
        x, y = -math.sin(th) * dist, -math.cos(th) * dist
        band = "near" if dist < P["near_limit_m"] else "mid" if dist < P["mid_limit_m"] else "far"
        if rng.random() > P["density"][band] or not free(x, y, 3):
            continue
        cat, cname = choose(dist, x, y)
        if cat == "garden":
            w = d = rng.uniform(12, 22)
            if not fits(x, y, w, d):
                continue
            for c in cells(x, y, w / 2):
                occ.add(c)
            for k in range(rng.randint(3, 7)):
                inst(rng.choice(lib["tree"]), x + rng.uniform(-w / 2, w / 2), y + rng.uniform(-d / 2, d / 2), 0, rng.uniform(0.8, 1.3), rng.uniform(0.8, 1.3), "Vegetation", "Tree")
            continue
        entry = rng.choice(lib[cat])
        sxy = rng.uniform(*fs)
        w, d = entry["dims"][0] * sxy, entry["dims"][1] * sxy
        if not fits(x, y, w, d):
            continue
        for c in cells(x, y, max(w, d) / 2 * 0.85):
            occ.add(c)
        yaw = district_yaw(x, y) + rng.choice((0.0, 0.0, math.pi / 2, -math.pi / 2, math.pi)) + rng.uniform(-0.05, 0.05)
        if cat in ("temple", "public") and dist < P["near_limit_m"]:
            yaw = district_yaw(x, y) + rng.uniform(-0.25, 0.25)   # fronts mostly toward the viewer
        sz = rng.uniform(*hs) if cat in ("small", "medium", "large", "mid", "far") else rng.uniform(0.9, 1.1)
        inst(entry, x, y, yaw, sxy, sz, cname)
        built += 1
        if rng.random() < P["tree_density"] and dist < P["mid_limit_m"]:
            inst(rng.choice(lib["tree"]), x + rng.uniform(-w / 2 - 3, w / 2 + 3), y + d / 2 + 2.5, 0, rng.uniform(0.8, 1.3), rng.uniform(0.8, 1.3), "Vegetation", "Tree")

    # the landmark temple inside its colonnaded precinct on the low hill (no grand staircase)
    lt = P["landmark_temple"]
    if greybox:
        a = Acc("TempleGrey")
        z = R.terrain_z(LT.x, LT.y)
        a.box((LT.x, LT.y, z + 12), (34, 50, 24), a.key("e8dcc8"))
        R.move_to(a.build(), "Temples & Monuments")
    else:
        landmark(lib, rng, LT, lt["scale"])
        # the forum: colonnades, banners, its statue fountain, an arch toward the precinct
        a = Acc("Forum")
        fx, fy = FORUM
        zf = R.terrain_z(fx, fy) + 0.3
        for side in (-1, 1):
            x0 = fx + side * 34
            for k in range(14):
                yy = fy - 28 + k * 4.3
                a.stack([(zf, T.ring(10, 0.55, 0.55, 0.04), x0, yy), (zf + 8, T.ring(10, 0.46, 0.46, 0.04), x0, yy)], a.key(T.MARBLE))
            a.box((x0, fy, zf + 8.5), (1.8, 58, 1.0), a.key(T.MARBLE))
            a.box((x0, fy, zf + 9.2), (1.9, 58, 0.4), a.key(T.CRIMSON))
            a.box((x0 + side * 5, fy, zf + 6.0), (8, 58, 12), a.key("efe2cc"))
            T.hip_roof_at(a, x0 + side * 4, fy, 11, 60, zf + 12)
            for k in range(4):
                T.banner_flat(a, (x0 - side * 1.0, fy - 22 + k * 14, zf + 8.2), 2.4, 5.8, -side * math.pi / 2)
        R.move_to(a.build(), "Public Buildings")
        inst(lib["monument"][2], fx, fy, 0, 1.4, 1.4, "Temples & Monuments", "ForumFountain")
        inst(lib["arch"][1], fx - 6, fy - 40, math.radians(-12), 1.0, 1.0, "Towers & Arches", "ForumArch")
        for k in range(16):
            ang = 2 * math.pi * k / 16
            inst(lib["tree"][k % 4], fx + math.cos(ang) * 30, fy + math.sin(ang) * 26, 0, 1.0, 1.0, "Vegetation", "Tree")
        # landmark palaces framing the middle ground
        for (lx, ly, i) in ((-118, -205, 1), (-160, -270, 4), (52, -240, 2), (-82, -150, 0)):
            inst(lib["large"][i], lx, ly, rng.uniform(-0.1, 0.1), 1.0, 1.0, "Residential", "Palace")
        # the aqueduct across the right distance, a gate, the theatre on the left
        p0, p1 = Vector((-2600, -2600)), Vector((-420, -1100))
        n = int((p1 - p0).length / 60)
        yaw = math.atan2((p1 - p0).y, (p1 - p0).x)
        for k in range(n):
            p = p0.lerp(p1, (k + 0.5) / n)
            inst(lib["arch"][3], p.x, p.y, yaw, 1.0, 1.0, "Towers & Arches", "Aqueduct")
        inst(lib["arch"][2], 560, -1500, 0.2, 1.0, 1.0, "Towers & Arches", "Gate")
        inst(lib["public"][2], 760, -1250, math.pi + 0.3, 1.6, 1.4, "Public Buildings", "Theatre")
    o = streets.build()
    R.move_to(o, "Streets & Plazas")
    print("city lots:", built, "instances:", STATS.get("n", 0))
    return built
