"""Alien planet prototype: procedural low-poly world built in Blender.

Run either:
    python3 alien_planet/blender/build_world.py            (pip `bpy` module)
    blender -b -P alien_planet/blender/build_world.py      (Blender 4.2+ / 5.x)

Writes
    alien_planet/blender/alien_world.blend   open and edit this in Blender
    alien_planet/godot/assets/world.glb      what Godot loads

Style rules (keep them when adding things):
- Flat-shaded low poly, colour lives in a per-face vertex colour (no textures), so the whole world uses
  five tiny materials: Terrain, Rock, Ruin, Flora and Glow.
- Geometry is merged into a few objects per 55 m chunk and category, which keeps mobile draw calls low
  and still lets the engine frustum-cull. Names carry meaning for Godot (see godot/scripts/world.gd):
    Terrain            ground mesh, gets trimesh collision
    Rock_*, Ruin_*     solid things, get trimesh collision
    Flora_*            plants, wind sway (UV.x = sway weight, UV.y = phase), no collision
    Deco_*             non-solid stone (stairs over a ramp, rubble, glyphs), no collision
    Detail_*           grass tufts, culled by distance
    Float_*            floating islands, bob slowly
- Blender is Z-up, 1 unit = 1 metre. The glTF export converts to Godot's Y-up: (x, y, z) -> (x, z, -y).
"""
import bpy, math, os, random, sys
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_GLB = os.path.join(ROOT, 'godot', 'assets', 'world.glb')
OUT_BLEND = os.path.join(HERE, 'alien_world.blend')

SEED = 1337
R = random.Random(SEED)

# ----------------------------------------------------------------------------------------------- layout
SIZE = 230.0          # terrain square, metres
GRID = 104            # quads per side (~2.2 m)
WATER = -1.2          # glowing lake surface (the plane itself is made in Godot)
LAKE = (14.0, -10.0, 25.0)
TEMPLE = (44.0, 32.0, 15.0, 8.0)                       # mesa with the ring shrine: x, y, radius, height
MESAS = [TEMPLE + (2.0,), (-58.0, -8.0, 11.0, 6.5, 1.6), (54.0, -46.0, 13.0, 11.0, 2.2),
         (-24.0, 58.0, 9.0, 5.0, 1.4)]
SPAWN = (-36.0, 16.0)
STAIR_DIR = Vector((-0.86, -0.51))                     # from temple centre towards spawn
PLANET_AZ = math.radians(20)                           # view axis: spawn facing and the shrine ring's facing
SUN_AZ, SUN_EL = math.radians(-62), math.radians(21)   # low warm sun in the south-east

CHUNK = 57.5
EXCL = []             # (x, y, r) circles where scatter must not go


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def fbm(x, y, octaves=4, seed=0.0):
    s, a, f, n = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        s += a * noise.noise(Vector((x * f, y * f, seed + o * 7.31)))
        n += a; a *= 0.5; f *= 2.03
    return s / n


def terrace(e, step):
    k = e / step
    f = math.floor(k)
    return (f + smooth(0.55, 1.0, k - f)) * step


def stair_geom():
    tx, ty, tr, th = TEMPLE
    foot = Vector((tx, ty)) + STAIR_DIR * (tr + 12.0)
    top = Vector((tx, ty)) + STAIR_DIR * (tr - 2.5)
    return foot, top


STAIR_FOOT, STAIR_TOP = stair_geom()


def base_height(x, y):
    """Height before the stair ramp is carved."""
    r = math.hypot(x, y)
    h = fbm(x * 0.017, y * 0.017) * 3.4 + fbm(x * 0.07 + 40, y * 0.07, 2) * 0.55
    # long wind-carved ridges
    h += 0.9 * abs(math.sin(x * 0.045 + y * 0.028 + fbm(x * 0.01, y * 0.01, 2, 5.0) * 3.5)) - 0.45
    # lake basin, warped edge
    lx, ly, lr = LAKE
    d = (math.hypot(x - lx, y - ly) + fbm(x * 0.05, y * 0.05, 2, 9.0) * 5.0) / lr
    h = lerp(-3.4 + fbm(x * 0.08, y * 0.08, 2, 15.0) * 0.8, h, smooth(0.35, 1.2, d))
    if d > 1.2:   # only the lake basin may dip below the water line (no stray puddles)
        h = max(h, WATER + 0.45 * smooth(1.2, 1.6, d))
    # terraced mesas with flat tops
    for i, (mx, my, mr, mh, st) in enumerate(MESAS):
        dd = math.hypot(x - mx, y - my) + fbm(x * 0.09, y * 0.09, 2, 20.0 + i) * (1.0 if i == 0 else 3.0)
        m = 1.0 - smooth(mr - 1.0, mr + (5.0 if i == 0 else 8.0), dd)
        if m > 0:
            flat = 1.0 - smooth(mr - 3.0, mr, dd)
            h = h * (1 - flat * (1.0 if i == 0 else 0.7)) + terrace(m * mh, st)
    # rim of terraced cliffs that encloses the explorable bowl
    e = smooth(62.0, 98.0, r + fbm(x * 0.03, y * 0.03, 3, 33.0) * 16.0)
    if e > 0:
        h += terrace(e * 36.0 + fbm(x * 0.05, y * 0.05, 2, 44.0) * 4.0 * e, 4.2)
    return h


def height(x, y):
    h = base_height(x, y)
    # ramp under the temple stairs (visual steps are non-solid Deco on top of this)
    p = Vector((x, y))
    a, b = STAIR_FOOT, STAIR_TOP
    ab = b - a
    t = clamp((p - a).dot(ab) / ab.length_squared)
    d = (a + ab * t - p).length
    if d < 6.0 and -0.05 < (p - a).dot(ab) / ab.length_squared < 1.05:
        h0 = base_height(a.x, a.y)
        ramp = lerp(h0, TEMPLE[3] + 0.05, t)
        w = 1.0 - smooth(2.6, 6.0, d)
        h = lerp(h, ramp, w) if t < 0.98 else h
    return h


# ----------------------------------------------------------------------------------------------- colours
def hexc(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def shade(c, k):
    return tuple(clamp(v * k) for v in c)


def jit(c, amt=0.05, rng=R):
    k = 1.0 + rng.uniform(-amt, amt)
    return shade(c, k)


C = {k: hexc(v) for k, v in dict(
    # Vibrant-but-natural palette: alien hues kept, saturation pulled towards real rock, sand and foliage.
    dust='#6a5468', mauve='#836272', dune='#b27f6c', moss='#3f7a66', mossl='#568c6c', shore='#bf9a74',
    wet='#9a8a66', bed='#7c7660', cliff1='#a8644c', cliff2='#7c5052', cliff3='#c9a070', cliff4='#5d4c5a',
    rock='#6c5a62', rock2='#96644e', rockt='#b48e72', slate='#4f4b60', slatet='#7c7690',
    ruin='#d6c6a4', ruind='#a8977c', ruinm='#7d9a7a', bone='#e6dcc4',
    trunk='#3e3038', trunk2='#5c4852', canopy='#c4486e', canopy2='#dc7890', coral='#e07450',
    teal='#33a084', tealtip='#78d2b0', amber='#e2a444', amberd='#d4603a', lime='#a4d85e',
    grass1='#4f9c6c', grass2='#88c28a', grass3='#c47490', grass4='#cc9e56',
    gcyan='#7ae6ee', glime='#c4f474', gpink='#f07cc6', gviolet='#9a8cf0', gglyph='#62eedc',
).items()}


# ----------------------------------------------------------------------------------------------- buckets
class Acc:
    __slots__ = ('v', 'f', 'fc', 'fm', 'uv')

    def __init__(self):
        self.v, self.f, self.fc, self.fm, self.uv = [], [], [], [], []


BUCKETS = {}
MATS = ['Terrain', 'Rock', 'Ruin', 'Flora', 'Glow']


def chunk_of(x, y):
    i = int(clamp((x + SIZE / 2) // CHUNK, 0, 3))
    j = int(clamp((y + SIZE / 2) // CHUNK, 0, 3))
    return f'{i}{j}'


def acc(name):
    a = BUCKETS.get(name)
    if a is None:
        a = BUCKETS[name] = Acc()
    return a


def face_normal(ps):
    n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
    return n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))


def emit(obj, mat, verts, faces, M, color, jitter=0.05, sway=None, phase=0.0):
    """Transform a primitive by M and append it to bucket `obj`.
    color: rgb tuple, or fn(face_index, centroid_world, normal_world) -> rgb.
    sway: None, or the height used to normalise the sway weight (local z / sway)."""
    a = acc(obj)
    base = len(a.v)
    wv = [M @ v for v in verts]
    a.v.extend(wv)
    if sway:
        a.uv.extend((clamp(v.z / sway) ** 1.6, phase) for v in verts)
    else:
        a.uv.extend((0.0, phase) for _ in verts)
    for fi, f in enumerate(faces):
        a.f.append(tuple(base + k for k in f))
        if callable(color):
            ps = [wv[k] for k in f]
            cen = sum(ps, Vector()) / len(ps)
            c = color(fi, cen, face_normal(ps))
        else:
            c = color
        a.fc.append(jit(c, jitter) if jitter else c)
        a.fm.append(mat)


# ----------------------------------------------------------------------------------------------- primitives
def ring_frame(t):
    t = t.normalized()
    up = Vector((0, 0, 1)) if abs(t.z) < 0.95 else Vector((1, 0, 0))
    u = t.cross(up).normalized()
    w = u.cross(t).normalized()
    return u, w


def prim_tube(path, n=6, cap_top=True, cap_bot=False, twist=0.0):
    """path: [(Vector pos, radius)], radius 0 at the end makes a point."""
    verts, faces = [], []
    rings = []
    for i, (p, r) in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)][0] - path[max(i - 1, 0)][0])
        u, w = ring_frame(t)
        if r <= 1e-6:
            rings.append([len(verts)]); verts.append(p.copy()); continue
        idx = []
        for k in range(n):
            a = 2 * math.pi * k / n + twist * i
            idx.append(len(verts))
            verts.append(p + (u * math.cos(a) + w * math.sin(a)) * r)
        rings.append(idx)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        if len(r1) == 1:
            for k in range(n):
                faces.append((r0[k], r0[(k + 1) % n], r1[0]))
        elif len(r0) == 1:
            for k in range(n):
                faces.append((r0[0], r1[(k + 1) % n], r1[k]))
        else:
            for k in range(n):
                faces.append((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    if cap_top and len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    if cap_bot and len(rings[0]) > 1:
        faces.append(tuple(reversed(rings[0])))
    return verts, faces


def prim_cyl(n, r0, r1, h, cap_top=True, cap_bot=False):
    return prim_tube([(Vector((0, 0, 0)), r0), (Vector((0, 0, h)), r1)], n, cap_top, cap_bot)


def prim_box(sx, sy, sz, taper=1.0):
    x, y = sx / 2, sy / 2
    xt, yt = x * taper, y * taper
    v = [Vector(p) for p in [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0),
                             (-xt, -yt, sz), (xt, -yt, sz), (xt, yt, sz), (-xt, yt, sz)]]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


_ICO = {}


def prim_ico(sub=1):
    if sub in _ICO:
        v, f = _ICO[sub]
        return [p.copy() for p in v], list(f)
    t = (1 + 5 ** 0.5) / 2
    v = [Vector(p).normalized() for p in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
                                         (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    for _ in range(sub):
        cache, nf = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                cache[k] = len(v); v.append(((v[a] + v[b]) / 2).normalized())
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    _ICO[sub] = (v, f)
    return prim_ico(sub)


def prim_rock(sub=1, rough=0.28, seed=0.0):
    v, f = prim_ico(sub)
    out = []
    for p in v:
        k = 1.0 + noise.noise(p * 1.7 + Vector((seed, seed * 0.7, 0))) * rough
        out.append(p * k)
    return out, f


def prim_blade(length, width, droop, segs=3, curl=0.0):
    """A leaf in the XZ plane growing along +X, drooping down at the tip."""
    v, f = [], []
    for i in range(segs + 1):
        t = i / segs
        x = length * t
        z = math.sin(t * math.pi * 0.55) * length * 0.35 - droop * t * t * length
        w = width * math.sin(math.pi * (0.15 + 0.85 * t)) * (1 - t * 0.85) if i < segs else 0.0
        if i < segs:
            v += [Vector((x, -w, z + curl * w)), Vector((x, w, z + curl * w))]
        else:
            v.append(Vector((x, 0, z)))
    for i in range(segs - 1):
        a = i * 2
        f.append((a, a + 1, a + 3, a + 2))
    a = (segs - 1) * 2
    f.append((a, a + 1, a + 2))
    return v, f


def mat_at(x, y, z, rz=0.0, s=1.0, tilt=(0.0, 0.0), sxyz=None):
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(tilt[0], 4, 'X') \
        @ Matrix.Rotation(tilt[1], 4, 'Y')
    if sxyz:
        return M @ Matrix.Diagonal((sxyz[0] * s, sxyz[1] * s, sxyz[2] * s, 1.0))
    return M @ Matrix.Scale(s, 4)


# ----------------------------------------------------------------------------------------------- terrain
GH = []   # grid heights
STEP = SIZE / GRID


def build_terrain():
    global GH
    GH = [[height(-SIZE / 2 + i * STEP, -SIZE / 2 + j * STEP) for j in range(GRID + 1)] for i in range(GRID + 1)]
    verts = [Vector((-SIZE / 2 + i * STEP, -SIZE / 2 + j * STEP, GH[i][j]))
             for i in range(GRID + 1) for j in range(GRID + 1)]
    faces = []
    idx = lambda i, j: i * (GRID + 1) + j
    for i in range(GRID):
        for j in range(GRID):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            if (i + j) % 2:
                faces += [(a, b, c), (a, c, d)]
            else:
                faces += [(a, b, d), (b, c, d)]
    lx, ly, lr = LAKE

    def col(fi, cen, n):
        x, y, z = cen
        slope = n.z
        if slope < 0.72:   # cliff faces: layered strata in height bands
            band = int(math.floor((z + fbm(x * 0.02, y * 0.02, 2, 3.0) * 3.0) / 2.6)) % 5
            c = [C['cliff1'], C['cliff3'], C['cliff2'], C['cliff1'], C['cliff4']][band]
            if z > 20:
                c = mix(c, C['cliff4'], 0.3)
            return shade(c, 0.8 + 0.3 * slope)
        if z < WATER - 0.2:
            c = mix(C['bed'], C['wet'], smooth(-3.6, WATER, z))
            return mix(c, C['moss'], 0.35 * smooth(0.0, 0.4, fbm(x * 0.1, y * 0.1, 2, 21.0)))   # weed patches
        dl = math.hypot(x - lx, y - ly) / lr
        b_forest = fbm(x * 0.025 + 100, y * 0.025, 3)
        b_meadow = fbm(x * 0.03 - 50, y * 0.03, 3, 2.0)
        c = mix(C['dust'], C['mauve'], smooth(-1.0, 3.0, z + fbm(x * 0.06, y * 0.06, 2) * 2))
        c = mix(c, C['dune'], smooth(0.25, 0.6, fbm(x * 0.02 + 7, y * 0.02, 2, 4.0)) * 0.7)
        if b_meadow > -0.02 and b_forest <= 0.06:
            mc = mix(C['moss'], C['mossl'], smooth(-0.3, 0.3, fbm(x * 0.12, y * 0.12, 2, 11.0)))
            c = mix(c, mc, smooth(-0.02, 0.2, b_meadow))
        if b_forest > 0.06:
            c = mix(c, C['cliff2'], smooth(0.06, 0.3, b_forest) * 0.6)
        if z < WATER + 1.4 and dl < 1.6:
            c = mix(C['shore'], c, smooth(WATER + 0.2, WATER + 1.4, z))
        if z > 14:
            c = mix(c, C['cliff3'], 0.4)
        return shade(c, 0.9 + 0.12 * slope)
    emit('Terrain', 'Terrain', verts, faces, Matrix.Identity(4), col, jitter=0.02)


def ground(x, y):
    """Exact height of the terrain mesh at (x, y)."""
    fx = (x + SIZE / 2) / STEP
    fy = (y + SIZE / 2) / STEP
    i = int(clamp(math.floor(fx), 0, GRID - 1))
    j = int(clamp(math.floor(fy), 0, GRID - 1))
    u, v = fx - i, fy - j
    h00, h10, h11, h01 = GH[i][j], GH[i + 1][j], GH[i + 1][j + 1], GH[i][j + 1]
    if (i + j) % 2:   # tris (a,b,c) (a,c,d): split along u == v
        if u >= v:
            return h00 + (h10 - h00) * u + (h11 - h10) * v
        return h00 + (h11 - h01) * u + (h01 - h00) * v
    if u + v <= 1:      # (a,b,d)
        return h00 + (h10 - h00) * u + (h01 - h00) * v
    return h11 + (h01 - h11) * (1 - u) + (h10 - h11) * (1 - v)


def slope_at(x, y, e=1.2):
    dx = ground(x + e, y) - ground(x - e, y)
    dy = ground(x, y + e) - ground(x, y - e)
    return math.hypot(dx, dy) / (2 * e)


def min_ground(x, y, r):
    return min(ground(x + dx * r, y + dy * r) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                                                              (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)))


def excluded(x, y, pad=0.0):
    return any(math.hypot(x - ex, y - ey) < er + pad for ex, ey, er in EXCL)


# ----------------------------------------------------------------------------------------------- rocks
def rock_col(base, top=None):
    top = top or C['rockt']

    def f(fi, cen, n):
        if n.z > 0.62:
            return mix(base, top, 0.55)
        band = math.sin(cen.z * 2.1 + cen.x * 0.1)
        return shade(base, 0.85 + 0.2 * band + 0.15 * n.z)
    return f


def boulder(x, y, s, z=None, obj=None, base=None, sink=0.35, flat=0.65, sub=1):
    z = ground(x, y) if z is None else z
    v, f = prim_rock(sub, 0.3, R.uniform(0, 100))
    sx, sy = R.uniform(0.8, 1.3), R.uniform(0.8, 1.3)
    M = mat_at(x, y, z - s * flat * sink, R.uniform(0, 6.3), s, (R.uniform(-0.2, 0.2), R.uniform(-0.2, 0.2)),
               (sx, sy, flat))
    base = base or (C['rock'] if R.random() < 0.6 else C['rock2'])
    emit(obj or f'Rock_{chunk_of(x, y)}', 'Rock', v, f, M, rock_col(base), 0.06)


def hoodoo(x, y, s):
    z = ground(x, y) - 0.4
    obj = f'Rock_{chunk_of(x, y)}'
    lean = Vector((R.uniform(-0.3, 0.3), R.uniform(-0.3, 0.3)))
    for k in range(R.randint(3, 4)):
        rr = s * (1.0 - k * 0.17)
        hh = rr * 1.1
        v, f = prim_rock(1, 0.22, R.uniform(0, 99))
        cx, cy = x + lean.x * k, y + lean.y * k
        M = mat_at(cx, cy, z + hh * 0.5, R.uniform(0, 6.3), 1.0, (0, 0), (rr, rr, hh * 0.62))
        emit(obj, 'Rock', v, f, M, rock_col(C['rock2'] if k % 2 else C['cliff3']), 0.05)
        z += hh * 0.95
    v, f = prim_rock(1, 0.2, R.uniform(0, 99))   # wide cap rock
    M = mat_at(x + lean.x * 4, y + lean.y * 4, z + s * 0.25, R.uniform(0, 6.3), 1.0, (R.uniform(-.15, .15), 0),
               (s * 1.9, s * 1.6, s * 0.55))
    emit(obj, 'Rock', v, f, M, rock_col(C['cliff2'], C['dune']), 0.05)
    EXCL.append((x, y, s * 1.4))


def thorn_spire(x, y, h, r0):
    z = ground(x, y) - 1.0
    bend = Vector((R.uniform(-1, 1), R.uniform(-1, 1), 0)).normalized() * h * R.uniform(0.12, 0.3)
    path = []
    n = 9
    for i in range(n + 1):
        t = i / n
        p = Vector((x, y, z + h * t)) + bend * (t * t)
        path.append((p, r0 * (1 - t) ** 0.9 * (1.0 + 0.12 * (i % 2))))
    v, f = prim_tube(path, 5, False, False, twist=0.25)

    def col(fi, cen, nn):
        band = (fi // 5) % 3
        return [C['bone'], C['cliff3'], C['cliff1']][band]
    emit(f'Rock_{chunk_of(x, y)}', 'Rock', v, f, Matrix.Identity(4), col, 0.04)
    EXCL.append((x, y, r0 + 0.8))


def natural_arch(cx, cy, span, height, rad, rz):
    d = Vector((math.cos(rz), math.sin(rz), 0))
    path = []
    n = 16
    for i in range(n + 1):
        a = math.pi * i / n
        p = Vector((cx, cy, 0)) + d * (-math.cos(a) * span / 2)
        p.z = math.sin(a) * height + lerp(ground(cx - d.x * span / 2, cy - d.y * span / 2),
                                          ground(cx + d.x * span / 2, cy + d.y * span / 2), i / n) - 2.0
        p += Vector((R.uniform(-.4, .4), R.uniform(-.4, .4), R.uniform(-.3, .3)))
        rr = rad * (1.35 - 0.5 * math.sin(a)) * R.uniform(0.9, 1.1)
        path.append((p, rr))
    v, f = prim_tube(path, 7, True, True, twist=0.3)
    v = [p + Vector((noise.noise(p * 0.4) * 0.5, noise.noise(p * 0.4 + Vector((5, 0, 0))) * 0.5, 0)) for p in v]

    def col(fi, cen, nn):
        if nn.z > 0.6:
            return C['dune']
        band = math.sin(cen.z * 1.6)
        return C['cliff1'] if band > 0.3 else C['cliff3'] if band > -0.3 else C['cliff2']
    emit(f'Rock_{chunk_of(cx, cy)}', 'Rock', v, f, Matrix.Identity(4), col, 0.05)
    for sgn in (-1, 1):
        fx, fy = cx + d.x * span / 2 * sgn, cy + d.y * span / 2 * sgn
        EXCL.append((fx, fy, rad * 1.6))
        for _ in range(4):
            boulder(fx + R.uniform(-4, 4), fy + R.uniform(-4, 4), R.uniform(0.8, 1.8))


def basalt_field(cx, cy, rad):
    obj = f'Rock_{chunk_of(cx, cy)}'
    s = 1.55
    for q in range(-12, 13):
        for r in range(-12, 13):
            x = cx + s * (q + r * 0.5)
            y = cy + s * r * 0.866
            d = math.hypot(x - cx, y - cy) + fbm(x * 0.2, y * 0.2, 2) * 3
            if d > rad:
                continue
            g = min_ground(x, y, 0.8)
            k = 1 - d / rad
            hh = 0.4 + k * 5.5 * (0.6 + 0.4 * fbm(x * 0.15, y * 0.15, 2, 3.3)) + R.uniform(0, 0.8)
            hh = round(hh / 0.45) * 0.45
            v, f = prim_cyl(6, s * 0.56, s * 0.53, hh + 1.0, True, False)
            M = mat_at(x, y, g - 1.0, math.pi / 6, 1.0, (R.uniform(-.03, .03), R.uniform(-.03, .03)))
            top_c = C['slatet'] if R.random() < 0.85 else C['moss']
            emit(obj, 'Rock', v, f, M, lambda fi, cen, nn, t=top_c: t if nn.z > 0.7 else
                 shade(C['slate'], 0.8 + 0.3 * abs(nn.x)), 0.06)
            if R.random() < 0.06:
                crystal_cluster(x, y, R.uniform(0.5, 0.8), z=g - 1.0 + hh + 1.0)
    EXCL.append((cx, cy, rad + 1))


# ----------------------------------------------------------------------------------------------- flora
def crystal_cluster(x, y, s, z=None, colour=None):
    z = ground(x, y) - 0.2 if z is None else z
    colour = colour or (C['gviolet'] if R.random() < 0.6 else C['gcyan'])
    obj = f'Flora_{chunk_of(x, y)}'
    for k in range(R.randint(3, 7)):
        h = s * R.uniform(1.0, 2.8) * (1.6 if k == 0 else 1.0)
        r = s * R.uniform(0.18, 0.32)
        v, f = prim_tube([(Vector((0, 0, -0.3)), r), (Vector((0, 0, h * 0.75)), r), (Vector((0, 0, h)), 0)], 6, False)
        tilt = (0, 0) if k == 0 else (R.uniform(-0.7, 0.7), R.uniform(-0.7, 0.7))
        M = mat_at(x + R.uniform(-.3, .3) * s, y + R.uniform(-.3, .3) * s, z, R.uniform(0, 6.3), 1.0, tilt)
        emit(obj, 'Glow', v, f, M, lambda fi, cen, nn: shade(colour, 0.55 + 0.45 * (fi % 2)), 0.06)


def parasol_tree(x, y, s, z=None, obj=None):
    z = ground(x, y) - 0.3 if z is None else z
    obj = obj or f'Flora_{chunk_of(x, y)}'
    H = R.uniform(7, 11.5) * s
    ph = R.random()
    bend = Vector((R.uniform(-1, 1), R.uniform(-1, 1), 0)).normalized() * H * R.uniform(0.08, 0.22)
    path = []
    for i in range(7):
        t = i / 6
        path.append((Vector((0, 0, H * t)) + bend * (t * t), lerp(0.5, 0.2, t) * s * (1.12 if i % 2 else 1.0)))
    v, f = prim_tube(path, 6, False, False, twist=0.2)
    M = mat_at(x, y, z, 0)
    emit(obj, 'Flora', v, f, M, lambda fi, cen, nn: C['trunk2'] if (fi // 6) % 2 else C['trunk'], 0.05, H, ph)
    top = Vector((0, 0, H)) + bend
    crad = R.uniform(3.4, 5.0) * s
    palette = R.choice([(C['canopy'], C['canopy2']), (C['coral'], C['canopy2']), (C['canopy'], C['coral'])])
    for layer, (rr, dz) in enumerate([(crad, 0.0), (crad * 0.55, 0.9 * s)]):
        n = 10 if layer == 0 else 8
        vv = [Vector((0, 0, 0.85 * s))]
        for k in range(n):
            a = 2 * math.pi * k / n
            vv.append(Vector((math.cos(a) * rr, math.sin(a) * rr, -0.55 * s - R.uniform(0, 0.3) * s)))
        ff = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
        Mc = mat_at(x + top.x, y + top.y, z + top.z + dz, R.uniform(0, 6.3), 1.0,
                    (R.uniform(-.12, .12), R.uniform(-.12, .12)))
        emit(obj, 'Flora', vv, ff, Mc, lambda fi, cen, nn, p=palette: p[fi % 2], 0.04, 0.0001, ph)
    for k in range(R.randint(4, 6)):   # glowing seed bulbs hanging under the canopy
        a = R.uniform(0, 6.3)
        rr = crad * R.uniform(0.35, 0.75)
        bv, bf = prim_ico(0)
        bz = top.z - 1.1 * s - R.uniform(0.4, 1.6) * s
        Mb = mat_at(x + top.x + math.cos(a) * rr, y + top.y + math.sin(a) * rr, z + bz, 0, 0.22 * s,
                    (0, 0), (1, 1, 1.4))
        emit(obj, 'Glow', bv, bf, Mb, C['gcyan'] if palette[0] != C['coral'] else C['glime'], 0.05, None, ph)
    EXCL.append((x, y, 1.0))


def bulb_pod(x, y, s):
    z = ground(x, y) - 0.1
    obj = f'Flora_{chunk_of(x, y)}'
    ph = R.random()
    glow = C['glime'] if R.random() < 0.55 else C['gpink']
    for k in range(R.randint(3, 6)):
        h = R.uniform(0.9, 2.6) * s
        a = R.uniform(0, 6.3)
        lean = Vector((math.cos(a), math.sin(a), 0)) * R.uniform(0.15, 0.6) * h
        path = [(Vector((0, 0, 0)), 0.09 * s), (lean * 0.3 + Vector((0, 0, h * 0.5)), 0.07 * s),
                (lean + Vector((0, 0, h)), 0.06 * s)]
        v, f = prim_tube(path, 4, False)
        M = mat_at(x, y, z, 0)
        emit(obj, 'Flora', v, f, M, C['teal'], 0.08, h, ph)
        bv, bf = prim_ico(0)
        br = R.uniform(0.2, 0.38) * s
        tip = lean + Vector((0, 0, h + br * 0.8))
        Mb = mat_at(x + tip.x, y + tip.y, z + tip.z, 0, br, (0, 0), (1, 1, 1.25))
        a_ = acc(obj); n0 = len(a_.v)
        emit(obj, 'Glow', bv, bf, Mb, lambda fi, cen, nn: shade(glow, 0.7 + 0.3 * (fi % 3 == 0)), 0.05, None, ph)
        for i in range(n0, len(a_.v)):
            a_.uv[i] = (1.0, ph)
    for k in range(R.randint(3, 5)):
        v, f = prim_blade(R.uniform(0.7, 1.2) * s, 0.22 * s, 0.6)
        emit(obj, 'Flora', v, f, mat_at(x, y, z, R.uniform(0, 6.3)), C['teal'], 0.08, 0.8 * s, ph)


def frond(x, y, s):
    z = ground(x, y) - 0.05
    obj = f'Flora_{chunk_of(x, y)}'
    ph = R.random()
    n = R.randint(5, 9)
    for k in range(n):
        L = R.uniform(1.4, 2.8) * s
        v, f = prim_blade(L, 0.35 * s, R.uniform(0.6, 1.1), 4, curl=0.4)
        M = mat_at(x, y, z, 2 * math.pi * k / n + R.uniform(-.2, .2), 1.0, (0, R.uniform(-0.5, -0.1)))
        emit(obj, 'Flora', v, f, M, lambda fi, cen, nn: mix(C['teal'], C['tealtip'], (fi % 4) / 3), 0.05,
             0.9 * s, ph)
    v, f = prim_tube([(Vector((0, 0, 0)), 0.1 * s), (Vector((0, 0, 1.8 * s)), 0.07 * s), (Vector((0, 0, 2.3 * s)), 0)],
                     4, False)
    emit(obj, 'Flora', v, f, mat_at(x, y, z), C['amber'], 0.05, 2.3 * s, ph)


def tube_coral(x, y, s):
    z = ground(x, y) - 0.15
    obj = f'Flora_{chunk_of(x, y)}'
    ph = R.random()
    for k in range(R.randint(4, 9)):
        h = R.uniform(0.5, 2.3) * s
        r = R.uniform(0.14, 0.32) * s
        v, f = prim_cyl(6, r, r * 1.25, h, True)
        M = mat_at(x + R.uniform(-.7, .7) * s, y + R.uniform(-.7, .7) * s, z, R.uniform(0, 6.3), 1.0,
                   (R.uniform(-.3, .3), R.uniform(-.3, .3)))
        emit(obj, 'Flora', v, f, M, lambda fi, cen, nn: C['amberd'] if fi == 6 else shade(C['amber'],
             0.8 + 0.2 * (fi % 2)), 0.08, h * 2.5, ph)


def lantern_stalk(x, y, s):
    z = ground(x, y) - 0.1
    obj = f'Flora_{chunk_of(x, y)}'
    ph = R.random()
    H = R.uniform(3.5, 6.5) * s
    bend = Vector((R.uniform(-1, 1), R.uniform(-1, 1), 0)).normalized() * H * 0.25
    path = [(Vector((0, 0, H * t)) + bend * (t * t), lerp(0.12, 0.05, t) * s) for t in (0, 0.3, 0.6, 0.85, 1.0)]
    v, f = prim_tube(path, 4, False)
    emit(obj, 'Flora', v, f, mat_at(x, y, z), C['trunk2'], 0.05, H, ph)
    for k in range(3):   # leaf pairs
        t = 0.25 + 0.2 * k
        p = Vector((0, 0, H * t)) + bend * (t * t)
        for side in (0, math.pi):
            lv, lf = prim_blade(0.9 * s, 0.18 * s, 0.9, 3)
            lv = [q + Vector((0, 0, 0)) for q in lv]
            M = mat_at(x + p.x, y + p.y, z + p.z, side + k * 1.1)
            a_ = acc(obj); n0 = len(a_.v)
            emit(obj, 'Flora', lv, lf, M, C['tealtip'], 0.06, None, ph)
            for i in range(n0, len(a_.v)):
                a_.uv[i] = (t ** 1.6, ph)
    bv, bf = prim_ico(1)
    tip = Vector((0, 0, H)) + bend
    glow = C['gpink'] if R.random() < 0.5 else C['gcyan']
    a_ = acc(obj); n0 = len(a_.v)
    emit(obj, 'Glow', bv, bf, mat_at(x + tip.x, y + tip.y, z + tip.z + 0.25 * s, 0, 0.3 * s, (0, 0), (1, 1, 1.5)),
         glow, 0.05, None, ph)
    for i in range(n0, len(a_.v)):
        a_.uv[i] = (1.0, ph)


def grass_tuft(x, y, palette):
    z = ground(x, y) - 0.05
    obj = f'Detail_{chunk_of(x, y)}'
    ph = R.random()
    c = R.choice(palette)
    v, f = [], []
    for k in range(R.randint(3, 5)):
        a = R.uniform(0, 6.3)
        h = R.uniform(0.3, 0.8)
        w = R.uniform(0.06, 0.12)
        ox, oy = R.uniform(-.25, .25), R.uniform(-.25, .25)
        lx, ly = math.cos(a), math.sin(a)
        b = len(v)
        v += [Vector((ox - ly * w, oy + lx * w, 0)), Vector((ox + ly * w, oy - lx * w, 0)),
              Vector((ox + lx * h * 0.4, oy + ly * h * 0.4, h))]
        f.append((b, b + 1, b + 2))
    emit(obj, 'Flora', v, f, mat_at(x, y, z), lambda fi, cen, nn: shade(c, 0.85 + 0.15 * (fi % 2)), 0.08, 0.8, ph)


# ----------------------------------------------------------------------------------------------- ruins
def ruin_col(glyph_ok=False):
    def f(fi, cen, n):
        if n.z > 0.7:
            return C['ruinm'] if noise.noise(cen * 0.6) > 0.25 else C['ruin']
        k = 0.82 + 0.18 * abs(n.x) + 0.05 * math.sin(cen.z * 3.0)
        base = C['ruind'] if noise.noise(cen * 0.35 + Vector((3, 1, 0))) > 0.3 else C['ruin']
        return shade(base, k)
    return f


def glyph_strip(obj, M, w, h, n):
    """Small glowing glyph blocks stacked vertically, in M's local frame (on +Y face)."""
    for k in range(n):
        gw = w * R.choice([0.35, 0.6, 0.9])
        v, f = prim_box(gw, 0.08, h * 0.6)
        emit(obj, 'Glow', v, f, M @ Matrix.Translation((R.uniform(-1, 1) * (w - gw) * 0.3, 0, k * h)), C['gglyph'],
             0.08)


def pillar(x, y, h, broken=False, tilt=(0, 0), z=None, obj=None, rz=None, glyphs=True):
    z = min_ground(x, y, 0.9) - 0.3 if z is None else z
    obj = obj or f'Ruin_{chunk_of(x, y)}'
    rz = R.uniform(0, 6.3) if rz is None else rz
    M = mat_at(x, y, z, rz, 1.0, tilt)
    v, f = prim_box(1.7, 1.7, 0.7, 0.92)
    emit(obj, 'Ruin', v, f, M, ruin_col(), 0.05)
    hs = h * (R.uniform(0.35, 0.75) if broken else 1.0)
    path = [(Vector((0, 0, 0.6)), 0.6), (Vector((0, 0, 0.6 + hs * 0.5)), 0.55), (Vector((0, 0, 0.6 + hs)), 0.52)]
    v, f = prim_tube(path, 8, True, False, twist=0.0)
    if broken:   # jagged top
        for i in range(16, 24):
            v[i] = v[i] + Vector((0, 0, R.uniform(-0.5, 0.25)))
    emit(obj, 'Ruin', v, f, M, ruin_col(), 0.05)
    if glyphs:
        gv, gf = prim_tube([(Vector((0, 0, 0.6 + hs * 0.38)), 0.6), (Vector((0, 0, 0.6 + hs * 0.38 + 0.22)), 0.6)],
                           8, False)
        gf = [ff for i, ff in enumerate(gf) if i % 2 == 0]
        emit(obj.replace('Ruin_', 'Deco_'), 'Glow', gv, gf, M, C['gglyph'], 0.05)
    if not broken:
        v, f = prim_box(1.8, 1.8, 0.55, 1.08)
        emit(obj, 'Ruin', v, f, M @ Matrix.Translation((0, 0, 0.6 + hs)), ruin_col(), 0.05)
    else:
        for _ in range(R.randint(1, 3)):   # the fallen part
            a = R.uniform(0, 6.3)
            d = R.uniform(1.8, 3.5)
            rx, ry = x + math.cos(a) * d, y + math.sin(a) * d
            seg = R.uniform(1.0, 2.2)
            v, f = prim_cyl(8, 0.52, 0.52, seg, True, True)
            Mr = mat_at(rx, ry, ground(rx, ry) + 0.25, a, 1.0, (math.pi / 2 + R.uniform(-.2, .2), 0))
            emit(obj.replace('Ruin_', 'Deco_'), 'Ruin', v, f, Mr, ruin_col(), 0.05)
    EXCL.append((x, y, 1.3))
    return z + 0.6 + hs + 0.55


def monolith(x, y, h, z=None, rz=0.0):
    z = min_ground(x, y, 1.0) - 0.6 if z is None else z
    obj = f'Ruin_{chunk_of(x, y)}'
    tilt = (R.uniform(-.06, .06), R.uniform(-.06, .06))
    M = mat_at(x, y, z, rz, 1.0, tilt)
    v, f = prim_box(1.5, 1.1, h, 0.62)
    emit(obj, 'Ruin', v, f, M, ruin_col(), 0.04)
    pv = [Vector((-0.465, -0.34, h)), Vector((0.465, -0.34, h)), Vector((0.465, 0.34, h)), Vector((-0.465, 0.34, h)),
          Vector((0, 0, h + 1.0))]
    pf = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    emit(obj, 'Ruin', pv, pf, M, ruin_col(), 0.04)
    for side in (0, math.pi):   # glyph columns on the two wide faces
        Mg = M @ Matrix.Rotation(side, 4, 'Z') @ Matrix.Translation((0, 0.47, h * 0.22))
        glyph_strip(f'Deco_{chunk_of(x, y)}', Mg @ Matrix.Rotation(math.atan2(0.2, h) * 1.0, 4, 'X'), 0.6, 0.55,
                    int(h * 0.55 / 0.55 * 0.9))
    EXCL.append((x, y, 1.6))


def block(obj, x, y, z, sx, sy, sz, rz=0.0, tilt=(0, 0), mat='Ruin'):
    v, f = prim_box(sx, sy, sz)
    emit(obj, mat, v, f, mat_at(x, y, z, rz, 1.0, tilt), ruin_col(), 0.06)


def rubble(x, y, n, spread):
    obj = f'Deco_{chunk_of(x, y)}'
    for _ in range(n):
        a, d = R.uniform(0, 6.3), R.uniform(0, spread)
        rx, ry = x + math.cos(a) * d, y + math.sin(a) * d
        s = R.uniform(0.3, 0.9)
        block(obj, rx, ry, ground(rx, ry) - s * 0.3, s * R.uniform(1, 1.8), s, s * 0.8, R.uniform(0, 6.3),
              (R.uniform(-.3, .3), R.uniform(-.3, .3)))


def wall_fragment(x, y, length, courses, rz):
    obj = f'Ruin_{chunk_of(x, y)}'
    d = Vector((math.cos(rz), math.sin(rz)))
    nb = int(length / 1.4)
    for c in range(courses):
        for b in range(nb):
            if c > 0 and R.random() < 0.15 + c * 0.18:
                continue
            off = (b - nb / 2 + 0.5 + (0.5 if c % 2 else 0)) * 1.4
            bx, by = x + d.x * off, y + d.y * off
            z0 = min_ground(x, y, length * 0.5) - 0.3
            block(obj, bx, by, z0 + c * 0.75, 1.36, 0.95, 0.72, rz + R.uniform(-.04, .04))
    EXCL.append((x, y, length * 0.55))
    rubble(x, y, 6, length * 0.7)


def stairs():
    a, b = STAIR_FOOT, STAIR_TOP
    obj = f'Deco_{chunk_of(a.x, a.y)}'
    ab = b - a
    n = int(ab.length / 0.7)
    rz = math.atan2(ab.y, ab.x)
    h0 = ground(a.x, a.y)
    h1 = TEMPLE[3]
    for k in range(n):
        t = (k + 0.5) / n
        p = a + ab * t
        top = lerp(h0, h1, (k + 1) / n) + 0.12
        block(obj, p.x, p.y, top - 1.6, ab.length / n + 0.05, 5.2, 1.6, rz)
    for side in (-1, 1):   # balustrade walls (solid, keep you on the stair)
        perp = Vector((-ab.y, ab.x)).normalized() * 3.0 * side
        for k in range(0, n, 3):
            t0 = k / n
            p = a + ab * (t0 + 1.5 / n) + perp
            top = lerp(h0, h1, t0 + 1.5 / n)
            if R.random() < 0.82:
                block(f'Ruin_{chunk_of(p.x, p.y)}', p.x, p.y, top - 1.2, ab.length / n * 3 + 0.05, 0.8,
                      2.0 + R.uniform(0, 0.4), rz)
    for side in (-1, 1):   # guardian monoliths at the foot
        perp = Vector((-ab.y, ab.x)).normalized() * 4.6 * side
        p = a - ab.normalized() * 1.0 + perp
        monolith(p.x, p.y, 5.0, rz=rz)
    for k in range(n):
        p = a + ab * ((k + 0.5) / n)
        EXCL.append((p.x, p.y, 3.4))


def ring_shrine():
    tx, ty, tr, th = TEMPLE
    obj = f'Ruin_{chunk_of(tx, ty)}'
    deco = f'Deco_{chunk_of(tx, ty)}'
    z = th
    # stepped octagonal dais (low steps, walkable via slopes)
    for k, (rr, hh) in enumerate([(9.0, 0.25), (7.0, 0.5), (5.2, 0.75)]):
        v, f = prim_cyl(8, rr, rr * 0.97, hh + 0.5, True)
        emit(deco, 'Ruin', v, f, mat_at(tx, ty, z - 0.5, math.pi / 8), ruin_col(), 0.04)
    v, f = prim_tube([(Vector((0, 0, 0)), 9.0), (Vector((0, 0, 0.9)), 5.2)], 8, True)   # invisible ramp collider
    emit(f'Ruin_{chunk_of(tx, ty)}', 'Ruin', v, f, mat_at(tx, ty, z - 0.15, math.pi / 8, 1.0, (0, 0),
                                                           (0.995, 0.995, 1.0)), ruin_col(), 0.04)
    # the great ring, standing on edge and facing the ringed planet
    face = PLANET_AZ
    rad = 6.2
    segs = 18
    missing = {4, 5}
    base_z = z + 0.75 + rad + 0.6
    axis_dir = Vector((math.cos(face), math.sin(face), 0))
    side_dir = Vector((-axis_dir.y, axis_dir.x, 0))
    for k in range(segs):
        a0 = 2 * math.pi * k / segs
        if k in missing:
            continue
        am = a0 + math.pi / segs
        c = Vector((tx, ty, base_z)) + side_dir * math.cos(am) * rad + Vector((0, 0, math.sin(am) * rad))
        seg_len = 2 * rad * math.sin(math.pi / segs) + 0.12
        v, f = prim_box(seg_len, 1.6, 1.3)
        v = [p - Vector((0, 0, 0.65)) for p in v]
        # orient: local X along the tangent in the side/up plane, local Y along axis_dir
        tang = side_dir * -math.sin(am) + Vector((0, 0, math.cos(am)))
        radial = side_dir * math.cos(am) + Vector((0, 0, math.sin(am)))
        M = Matrix(((tang.x, axis_dir.x, radial.x, c.x), (tang.y, axis_dir.y, radial.y, c.y),
                    (tang.z, axis_dir.z, radial.z, c.z), (0, 0, 0, 1)))
        emit(obj, 'Ruin', v, f, M, ruin_col(), 0.04)
        gv, gf = prim_box(seg_len * 0.7, 1.7, 0.12)
        gv = [p - Vector((0, 0, 0.72)) for p in gv]
        emit(deco, 'Glow', gv, gf, M, C['gglyph'], 0.05)
    # the two fallen segments
    for k, off in zip(missing, (-1, 1)):
        p = Vector((tx, ty)) + side_dir.xy * (rad + 2.5) * off + axis_dir.xy * R.uniform(1.5, 3)
        block(obj, p.x, p.y, ground(p.x, p.y) - 0.3, 2.3, 1.6, 1.3, face + R.uniform(-.6, .6),
              (R.uniform(-.25, .25), R.uniform(-.25, .25)))
    # ring feet
    for off in (-1, 1):
        p = Vector((tx, ty)) + side_dir.xy * (rad * 0.62) * off
        block(obj, p.x, p.y, z + 0.5, 2.0, 2.4, 2.2, face)
    # circle of monoliths around the dais
    for k in range(7):
        a = face + math.pi / 7 + 2 * math.pi * k / 7
        p = Vector((tx, ty)) + Vector((math.cos(a), math.sin(a))) * 11.5
        if k == 3:   # the toppled one
            v, f = prim_box(1.5, 1.1, 6.0, 0.62)
            emit(obj, 'Ruin', v, f, mat_at(p.x, p.y, th + 0.2, a + 0.4, 1.0, (math.pi / 2 - 0.12, 0)),
                 ruin_col(), 0.04)
            continue
        monolith(p.x, p.y, R.uniform(4.5, 6.5), z=th - 0.4, rz=a + math.pi / 2)
    # the floating core: its own object so Godot can spin and bob it
    v, f = prim_ico(0)
    emit('Float_core', 'Glow', v, f, mat_at(0, 0, 0, 0, 0.9, (0, 0), (1, 1, 1.7)),
         lambda fi, cen, nn: shade(C['gcyan'], 0.6 + 0.4 * (fi % 2)), 0.0)
    CORE_POS[:] = [tx, ty, base_z]
    EXCL.append((tx, ty, 13.5))
    rubble(tx, ty, 18, 12)


CORE_POS = [0.0, 0.0, 0.0]


def colonnade(a, b, n):
    a, b = Vector(a), Vector(b)
    d = b - a
    rz = math.atan2(d.y, d.x)
    perp = Vector((-d.y, d.x)).normalized() * 3.2
    tops = {}
    for k in range(n):
        for side in (-1, 1):
            p = a + d * (k / (n - 1)) + perp * side
            broken = R.random() < 0.45
            if R.random() < 0.12:
                rubble(p.x, p.y, 4, 2.0)
                continue
            top = pillar(p.x, p.y, R.uniform(4.8, 5.6), broken, (R.uniform(-.05, .05), R.uniform(-.05, .05)),
                         rz=rz)
            if not broken:
                tops[(k, side)] = (p, top)
    for (k, side), (p, top) in tops.items():   # surviving lintels
        if (k + 1, side) in tops:
            q, top2 = tops[(k + 1, side)]
            m = (p + q) / 2
            block(f'Ruin_{chunk_of(m.x, m.y)}', m.x, m.y, min(top, top2), (q - p).length + 1.4, 1.2, 0.8, rz)
    for k in range(n):   # paving under the walk, half buried
        p = a + d * (k / (n - 1))
        for side in (-1, 0, 1):
            q = p + perp * side * 0.55
            if R.random() < 0.7:
                block(f'Deco_{chunk_of(q.x, q.y)}', q.x, q.y, ground(q.x, q.y) - 0.45, 1.6, 1.7, 0.55,
                      rz + R.uniform(-.1, .1), (R.uniform(-.05, .05), R.uniform(-.05, .05)))
    for k in range(n):
        p = a + d * (k / (n - 1))
        EXCL.append((p.x, p.y, 4.0))


def gateway(x, y, rz):
    obj = f'Ruin_{chunk_of(x, y)}'
    d = Vector((math.cos(rz), math.sin(rz)))
    z = min_ground(x, y, 6) - 2.0
    tilt = (0.07, 0.0)
    M = mat_at(x, y, z, rz, 1.0, tilt)
    for side in (-1, 1):
        v, f = prim_box(2.4, 2.4, 12.0, 0.8)
        emit(obj, 'Ruin', v, f, M @ Matrix.Translation((side * 4.2, 0, 0)), ruin_col(), 0.04)
        glyph_strip(f'Deco_{chunk_of(x, y)}', M @ Matrix.Translation((side * 4.2, -1.1, 3.0)) @
                    Matrix.Rotation(math.pi, 4, 'Z'), 1.2, 0.7, 9)
    v, f = prim_box(12.5, 3.0, 2.2)
    emit(obj, 'Ruin', v, f, M @ Matrix.Translation((0, 0, 11.6)) @ Matrix.Rotation(0.05, 4, 'Y'), ruin_col(), 0.04)
    v, f = prim_box(6.0, 3.2, 1.0, 0.7)
    emit(obj, 'Ruin', v, f, M @ Matrix.Translation((0, 0, 13.7)), ruin_col(), 0.04)
    gv, gf = prim_box(5.0, 3.1, 0.25)
    emit(f'Deco_{chunk_of(x, y)}', 'Glow', gv, gf, M @ Matrix.Translation((0, 0, 12.4)), C['gglyph'], 0.05)
    EXCL.append((x - d.y * 4.2, y + d.x * 4.2, 2.5)); EXCL.append((x + d.y * 4.2, y - d.x * 4.2, 2.5))
    rubble(x, y, 10, 8)


# ----------------------------------------------------------------------------------------------- floating islands
def floating_island(i, cx, cy, cz, rad):
    obj = f'Float_{i}'
    n = 8
    path = [(Vector((0, 0, -rad * 1.9)), 0), (Vector((0, 0, -rad * 1.0)), rad * 0.45),
            (Vector((0, 0, -rad * 0.35)), rad * 0.85), (Vector((0, 0, 0)), rad)]
    v, f = prim_tube(path, n, True, False, twist=0.35)
    v = [p + Vector((noise.noise(p * 0.5 + Vector((i, 0, 0))) * rad * 0.18, noise.noise(p * 0.5 + Vector((0, i, 3)))
                     * rad * 0.18, 0 if p.z > -0.01 else noise.noise(p * 0.3) * rad * 0.2)) for p in v]
    emit(obj, 'Rock', v, f, Matrix.Identity(4), lambda fi, cen, nn: C['moss'] if nn.z > 0.8 else
         ([C['cliff1'], C['cliff3'], C['cliff2']][(fi // n) % 3]), 0.05)
    for k in range(R.randint(2, 4)):   # hanging rock drips
        a = R.uniform(0, 6.3)
        rr = rad * R.uniform(0.3, 0.7)
        dv, df = prim_tube([(Vector((0, 0, 0)), rad * 0.22), (Vector((0, 0, -rad * R.uniform(0.6, 1.2))), 0)], 5,
                           False)
        emit(obj, 'Rock', dv, df, Matrix.Translation((math.cos(a) * rr, math.sin(a) * rr, -rad * 0.4)), C['cliff2'],
             0.05)
    if rad > 4:
        parasol_tree(0, 0, 0.6 + rad * 0.04, z=-0.3, obj=obj)
    for k in range(int(rad * 1.5)):
        a, d = R.uniform(0, 6.3), R.uniform(0, rad * 0.8)
        x, y = math.cos(a) * d, math.sin(a) * d
        v, f = prim_rock(0, 0.3, R.random() * 9)
        if R.random() < 0.3:
            emit(obj, 'Rock', v, f, mat_at(x, y, 0, 0, R.uniform(0.3, 0.7), (0, 0), (1, 1, 0.6)), C['rock'], 0.05)
        else:   # glowing moss tufts
            gv, gf = prim_tube([(Vector((0, 0, 0)), 0.12), (Vector((0, 0, R.uniform(0.3, 0.8))), 0)], 4, False)
            emit(obj, 'Glow', gv, gf, mat_at(x, y, 0), C['glime'] if k % 2 else C['gcyan'], 0.05)
    FLOATS.append((obj, (cx, cy, cz)))


FLOATS = []


# ----------------------------------------------------------------------------------------------- scatter
GROVES = [(-58, -16, 13, 9), (-46, 46, 11, 7), (2, 30, 10, 6), (28, 12, 9, 5), (60, -12, 11, 7), (-14, -30, 8, 4)]


def groves():
    n = 0
    for gx, gy, gr, count in GROVES:
        placed = []
        for _ in range(count * 12):
            if len(placed) >= count:
                break
            a, d = R.uniform(0, 6.3), gr * math.sqrt(R.random())
            x, y = gx + math.cos(a) * d, gy + math.sin(a) * d
            if math.hypot(x - SPAWN[0], y - SPAWN[1]) < 8 or excluded(x, y, 1.5):
                continue
            if ground(x, y) < WATER + 0.6 or slope_at(x, y) > 0.4:
                continue
            if any(math.hypot(x - px, y - py) < 5.0 for px, py in placed):
                continue
            parasol_tree(x, y, R.uniform(0.85, 1.35))
            placed.append((x, y)); n += 1
            for _ in range(2):
                bx, by = x + R.uniform(-3, 3), y + R.uniform(-3, 3)
                if not excluded(bx, by) and ground(bx, by) > WATER + 0.3:
                    bulb_pod(bx, by, R.uniform(0.7, 1.1))
    return n


def lakebed():
    """Rocks, weed and crystals on the lake floor so the clear water has something to show."""
    lx, ly, lr = LAKE
    n = 0
    for _ in range(900):
        a, d = R.uniform(0, 6.3), lr * 1.3 * math.sqrt(R.random())
        x, y = lx + math.cos(a) * d, ly + math.sin(a) * d
        g = ground(x, y)
        if g > WATER - 0.35 or excluded(x, y):
            continue
        roll = R.random()
        if roll < 0.09:
            boulder(x, y, R.uniform(0.4, 1.6), base=C['rock'] if R.random() < 0.5 else C['slate'])
        elif roll < 0.42:   # swaying weed
            obj = f'Flora_{chunk_of(x, y)}'
            ph = R.random()
            for k in range(R.randint(3, 6)):
                h = min(R.uniform(0.6, 2.0), WATER - g - 0.2)
                if h < 0.3:
                    continue
                lean = Vector((R.uniform(-.3, .3), R.uniform(-.3, .3), 0))
                path = [(Vector((0, 0, 0)), 0.08), (lean * 0.5 + Vector((0, 0, h * 0.5)), 0.07), (lean + Vector((0, 0, h)), 0)]
                v, f = prim_tube(path, 3, False)
                emit(obj, 'Flora', v, f, mat_at(x + R.uniform(-.3, .3), y + R.uniform(-.3, .3), g - 0.05),
                     C['moss'] if k % 2 else C['teal'], 0.08, h, ph)
        elif roll < 0.5:
            tube_coral(x, y, R.uniform(0.6, 1.0))
        elif roll < 0.53:
            crystal_cluster(x, y, R.uniform(0.4, 0.8), colour=C['gcyan'])
        else:
            continue
        n += 1
    return n


def scatter():
    lx, ly, lr = LAKE
    counts = {}

    def bump(k):
        counts[k] = counts.get(k, 0) + 1
    sp = 2.6
    n = int(SIZE / sp)
    for i in range(n):
        for j in range(n):
            x = -SIZE / 2 + (i + R.random()) * sp
            y = -SIZE / 2 + (j + R.random()) * sp
            r = math.hypot(x, y)
            if r > 92:
                continue
            g = ground(x, y)
            sl = slope_at(x, y)
            if g < WATER + 0.25 or sl > 0.55:
                if sl > 0.55 and g > WATER and R.random() < 0.05:
                    boulder(x, y, R.uniform(0.8, 2.2)); bump('boulder')
                continue
            if excluded(x, y):
                continue
            near_spawn = math.hypot(x - SPAWN[0], y - SPAWN[1]) < 9
            if math.hypot(x - SPAWN[0], y - SPAWN[1]) < 4.5 and R.random() < 0.7:
                continue
            forest = fbm(x * 0.025 + 100, y * 0.025, 3)
            meadow = fbm(x * 0.03 - 50, y * 0.03, 3, 2.0)
            dl = math.hypot(x - lx, y - ly) / lr
            shore = g < WATER + 2.2 and dl < 1.7
            roll = R.random()
            if shore:
                if roll < 0.17:
                    tube_coral(x, y, R.uniform(0.7, 1.3)); bump('coral')
                elif roll < 0.21:
                    crystal_cluster(x, y, R.uniform(0.5, 1.0)); bump('crystal')
                elif roll < 0.6:
                    grass_tuft(x, y, [C['grass4'], C['amber'], C['grass3']]); bump('tuft')
            elif forest > 0.06:
                if roll < 0.075 and not near_spawn and sl < 0.35:
                    parasol_tree(x, y, R.uniform(0.85, 1.3)); bump('parasol')
                elif roll < 0.13:
                    bulb_pod(x, y, R.uniform(0.8, 1.3)); bump('bulb')
                elif roll < 0.165 and not near_spawn:
                    lantern_stalk(x, y, R.uniform(0.8, 1.2)); bump('lantern')
                elif roll < 0.6:
                    grass_tuft(x, y, [C['grass3'], C['grass1'], C['canopy2']]); bump('tuft')
            elif meadow > -0.02:
                if roll < 0.09 and not near_spawn:
                    frond(x, y, R.uniform(0.8, 1.3)); bump('frond')
                elif roll < 0.12:
                    bulb_pod(x, y, R.uniform(0.6, 1.0)); bump('bulb')
                elif roll < 0.75:
                    grass_tuft(x, y, [C['grass1'], C['grass2'], C['tealtip']]); bump('tuft')
            else:
                if roll < 0.035:
                    boulder(x, y, R.uniform(0.6, 2.4)); bump('boulder')
                elif roll < 0.05:
                    frond(x, y, R.uniform(0.6, 0.9)); bump('frond')
                elif roll < 0.058 and not near_spawn:
                    lantern_stalk(x, y, R.uniform(0.7, 1.0)); bump('lantern')
                elif roll < 0.064:
                    crystal_cluster(x, y, R.uniform(0.5, 1.1)); bump('crystal')
                elif roll < 0.35:
                    grass_tuft(x, y, [C['grass1'], C['grass3'], C['grass4']]); bump('tuft')
    return counts


# ----------------------------------------------------------------------------------------------- baked ambient occlusion
AO_RAYS = 14
AO_DIST = 6.0
AO_TINT = (0.40, 0.34, 0.58)   # occluded areas shift towards dusk violet instead of going grey


def _hemisphere(n):
    dirs = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - (i + 0.5) / n          # cosine-ish spread, denser near the horizon is avoided by sqrt
        z = math.sqrt(z)
        r = math.sqrt(max(0.0, 1 - z * z))
        a = ga * i
        dirs.append(Vector((math.cos(a) * r, math.sin(a) * r, z)))
    return dirs


def bake_ao():
    """Per-face ambient occlusion baked into the vertex colours (free at runtime, which suits mobile).
    Occluders: everything except grass tufts and the floating islands (those get self-occlusion only)."""
    t0 = __import__('time').time()
    verts, polys = [], []
    for name, a in BUCKETS.items():
        if name.startswith('Detail_') or name.startswith('Float_'):
            continue
        base = len(verts)
        verts.extend(a.v)
        polys.extend(tuple(base + k for k in f) for f in a.f)
    tree = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    hemi = _hemisphere(AO_RAYS)
    rnd = random.Random(7)
    n_faces = 0
    for name, a in BUCKETS.items():
        local_tree = None
        if name.startswith('Float_'):
            local_tree = BVHTree.FromPolygons(a.v, a.f, all_triangles=False, epsilon=0.0)
        tr = local_tree or tree
        for fi, f in enumerate(a.f):
            if a.fm[fi] == 'Glow':
                continue
            ps = [a.v[k] for k in f]
            cen = sum(ps, Vector()) / len(ps)
            nrm = face_normal(ps)
            if name.startswith('Detail_'):   # grass: darker the lower the blade sits
                nrm = Vector((0, 0, 1))
            u, w = ring_frame(nrm)
            rot = rnd.uniform(0, 6.283)
            cr, sr = math.cos(rot), math.sin(rot)
            org = cen + nrm * 0.06
            occ = 0.0
            small = a.fm[fi] == 'Flora'
            dist = 2.5 if small else AO_DIST
            for d in hemi:
                dx, dy = d.x * cr - d.y * sr, d.x * sr + d.y * cr
                ray = (u * dx + w * dy + nrm * d.z).normalized()
                hit = tr.ray_cast(org, ray, dist)
                # a back-face hit means the ray started inside an overlapping solid (stacked stones): ignore
                if hit[0] is not None and hit[1].dot(ray) < 0:
                    occ += 1.0 - (hit[3] / dist) ** 0.7
            ao = 1.0 - min(1.0, occ / AO_RAYS * 1.15)
            k = ao ** 1.2
            c = a.fc[fi]
            a.fc[fi] = tuple(c[i] * lerp(AO_TINT[i], 1.0, k) for i in range(3))
            n_faces += 1
    print(f'ao: {n_faces} faces in {__import__("time").time() - t0:.1f}s')


# ----------------------------------------------------------------------------------------------- blender scene
def make_materials():
    mats = {}
    for name in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
        nt.links.new(ca.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 1.0
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.0
        if name == 'Glow':
            nt.links.new(ca.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 2.0
        mats[name] = m
    return mats


def build_object(name, a, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in a.v], [], a.f)
    used = [m for m in MATS if m in set(a.fm)]
    for m in used:
        me.materials.append(mats[m])
    mi = {m: i for i, m in enumerate(used)}
    me.polygons.foreach_set('material_index', [mi[m] for m in a.fm])
    col = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    loop_cols = [0.0] * (len(me.loops) * 4)
    loop_uv = [0.0] * (len(me.loops) * 2)
    lv = [0] * len(me.loops)
    me.loops.foreach_get('vertex_index', lv)
    for p in me.polygons:
        c = a.fc[p.index]
        for li in p.loop_indices:
            loop_cols[li * 4:li * 4 + 4] = (c[0], c[1], c[2], 1.0)
            u = a.uv[lv[li]]
            loop_uv[li * 2:li * 2 + 2] = (u[0], u[1])
    col.data.foreach_set('color_srgb', loop_cols)
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = 0
    uv = me.uv_layers.new(name='Sway')
    uv.data.foreach_set('uv', loop_uv)
    if hasattr(me, 'shade_flat'):
        me.shade_flat()
    else:
        me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    t0 = __import__('time').time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_terrain()
    # features first (they claim space), scatter last
    ring_shrine()
    stairs()
    colonnade((-30.0, 6.0), (-8.0, -2.0), 6)
    gateway(-16.0, 42.0, math.radians(-25))
    for (x, y) in [(-6, 30), (24, 6), (-44, -26), (36, -16), (64, 16)]:
        wall_fragment(x, y, R.uniform(5, 9), R.randint(2, 4), R.uniform(0, 3.1))
    for x, y in [(-50, 34), (-2, -36), (30, -30), (-28, -8), (6, 22)]:
        monolith(x, y, R.uniform(4.5, 7.5), rz=R.uniform(0, 3.1))
    natural_arch(32.0, -44.0, 26.0, 15.0, 2.6, math.radians(70))
    basalt_field(-40.0, -38.0, 13.0)
    for (x, y, h) in [(62, 6, 16), (66, 12, 11), (58, 0, 9), (-62, 30, 14), (-58, 36, 9), (10, 50, 12), (20, 58, 8)]:
        thorn_spire(x, y, h, h * 0.13)
    for (x, y, s) in [(-12, -50, 2.2), (-8, 22, 1.6), (22, 48, 2.0), (-60, 10, 1.8), (48, -10, 2.3)]:
        hoodoo(x, y, s)
    for k, (x, y, z, r) in enumerate([(8, -14, 15, 6), (26, -4, 22, 4.2), (-2, -22, 11, 3.2), (28, -22, 28, 5)]):
        floating_island(k, x, y, z, r)
    for (x, y, s) in [(-26, -40, 1.4), (20, -34, 1.2), (-6, 4, 1.0), (52, 22, 1.1), (-48, -14, 1.3), (6, 36, 1.0)]:
        crystal_cluster(x, y, s)
    n_trees = groves()
    counts = scatter()
    counts['lakebed'] = lakebed()
    counts['grove_trees'] = n_trees

    bake_ao()
    mats = make_materials()
    objs = []
    for name in sorted(BUCKETS):
        objs.append(build_object(name, BUCKETS[name], mats))
    for ob in objs:   # float origins
        if ob.name.startswith('Float_') and ob.name != 'Float_core':
            pos = dict(FLOATS)[ob.name]
            ob.location = pos
        if ob.name == 'Float_core':
            ob.location = CORE_POS

    tris = sum(len(BUCKETS[n].f) for n in BUCKETS)
    print('objects', len(objs), 'faces', tris, 'counts', counts)
    for ob in objs:
        ob.select_set(True)
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                              export_texcoords=True, export_normals=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False)
    # a pleasant view when the .blend is opened
    scn = bpy.context.scene
    w = bpy.data.worlds.new('AlienSky'); scn.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.45, 0.32, 0.5, 1)
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 3.0; sun.data.color = (1.0, 0.78, 0.6)
    sd = Vector((math.cos(SUN_EL) * math.cos(SUN_AZ), math.cos(SUN_EL) * math.sin(SUN_AZ), math.sin(SUN_EL)))
    sun.rotation_euler = (-sd).to_track_quat('-Z', 'Y').to_euler()
    scn.collection.objects.link(sun)
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    cam.data.clip_end = 400; cam.data.lens = 22
    cam.location = (SPAWN[0], SPAWN[1], ground(*SPAWN) + 1.7)
    cam.rotation_euler = (math.radians(88), 0, PLANET_AZ - math.pi / 2)
    scn.collection.objects.link(cam); scn.camera = cam
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print(f'wrote {OUT_GLB} ({os.path.getsize(OUT_GLB) / 1e6:.2f} MB) and {OUT_BLEND} in '
          f'{__import__("time").time() - t0:.1f}s')
    print('spawn', SPAWN, ground(*SPAWN), 'water', WATER, 'lake', LAKE, 'core', CORE_POS)


if __name__ == '__main__':
    main()
