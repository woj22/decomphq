"""Farming valley: fields of wind-blown alien wheat, row crops, homesteads and farm machinery.

Called from build_world.py (`farm.build(W)`, W = the build_world module), which also uses the layout
constants here to shape the terrain (valley floor, pass through the northern cliffs, field soil colours).

Named objects with motion (Godot animates them by name, see godot/scripts/main.gd):
    Spin_<axis>_<speed>_<id>   rotates about its local Godot axis (x/y/z) at <speed>/100 rad/s
    Mover_<dist>_<id>          glides back and forth <dist> metres along its local X, hovering slightly
Other prefixes: Build_* solid farm buildings (collision), Wheat_* wheat (wind shader), Crop_* row crops.
"""
import math
from mathutils import Vector, Matrix

# ------------------------------------------------------------------------------------------------ layout (Blender XY)
VALLEY = (-4.0, 104.0, 62.0, 34.0)          # ellipse centre x, y and radii
PASS = ((-4.0, 48.0), (-4.0, 80.0), 11.0)   # capsule through the northern rim: a, b, radius
# fields: (x, y, width, length, angle, crop, variety)
FIELDS = [
    (-42.0, 92.0, 20.0, 14.0, 0.10, 'wheat', 'gold'),
    (-44.0, 114.0, 20.0, 14.0, 0.06, 'wheat', 'copper'),
    (-18.0, 88.0, 16.0, 12.0, -0.05, 'bulbroot', None),
    (-8.0, 122.0, 24.0, 14.0, 0.0, 'wheat', 'gold'),
    (14.0, 90.0, 16.0, 12.0, 0.08, 'kale', None),
    (38.0, 98.0, 11.5, 11.5, 0.0, 'wheat_round', 'pale'),
    (34.0, 118.0, 16.0, 10.0, -0.1, 'wheat', 'copper'),
]
YARDS = [(-26.0, 106.0, 9.0), (18.0, 112.0, 8.0)]     # packed-earth farmyards: x, y, radius
ROADS = [((-4.0, 60.0), (-4.0, 104.0)), ((-4.0, 104.0), (-26.0, 106.0)), ((-4.0, 104.0), (18.0, 112.0)),
         ((18.0, 112.0), (38.0, 110.0)), ((-26.0, 106.0), (-44.0, 103.0))]
HARVESTED = 0.42   # southern fraction of field 3 already cut (the harvester works its edge)

WHEAT = {'gold': ('#c8a040', '#ecbc48'), 'copper': ('#c09040', '#e0a040'), 'pale': ('#c8b060', '#f0d478')}
CANOPY = {'gold': ('#c09034', '#d0a040', '#a87a2a'), 'copper': ('#b8823a', '#c8943e', '#9a6a2c'),
          'pale': ('#c8aa58', '#d8bc68', '#ae9244')}


def ellipse_d(x, y):
    cx, cy, rx, ry = VALLEY
    q = math.hypot((x - cx) / rx, (y - cy) / ry)
    return (q - 1.0) * ry


def capsule_d(x, y, a, b, r):
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    t = max(0.0, min(1.0, ((x - ax) * abx + (y - ay) * aby) / (abx * abx + aby * aby)))
    return math.hypot(x - (ax + abx * t), y - (ay + aby * t)) - r


def field_local(f, x, y):
    fx, fy, w, l, a = f[:5]
    dx, dy = x - fx, y - fy
    c, s = math.cos(-a), math.sin(-a)
    return dx * c - dy * s, dx * s + dy * c


def in_field(x, y, pad=0.0):
    for i, f in enumerate(FIELDS):
        if f[5] == 'wheat_round':
            if math.hypot(x - f[0], y - f[1]) < f[2] + pad:
                return i
            continue
        lx, ly = field_local(f, x, y)
        if abs(lx) < f[2] / 2 + pad and abs(ly) < f[3] / 2 + pad:
            return i
    return None


def road_d(x, y):
    return min(capsule_d(x, y, a, b, 0.0) for a, b in ROADS)


def ground_colour(W, x, y, z, base):
    """Soil, roads and yards inside the valley (called from the terrain colouring)."""
    C = W.C
    fi = in_field(x, y, 0.6)
    if fi is not None:
        crop = FIELDS[fi][5]
        soil = W.hexc('#6a4c36') if crop in ('bulbroot', 'kale') else W.hexc('#a08a48')
        return W.shade(soil, 0.92 + 0.12 * W.fbm(x * 0.4, y * 0.4, 1, 3.0))
    if any(math.hypot(x - yx, y - yy) < yr for yx, yy, yr in YARDS):
        return W.hexc('#b49470')
    rd = road_d(x, y)
    if rd < 1.8:
        return W.mix(W.hexc('#b48c5c'), meadow(W, x, y), W.smooth(1.0, 1.8, rd))
    return meadow(W, x, y)


def meadow(W, x, y):
    n = W.fbm(x * 0.05, y * 0.05, 2, 61.0)
    c = W.mix(W.hexc('#557f3c'), W.hexc('#759a48'), W.smooth(-0.3, 0.3, n))
    return W.mix(c, W.hexc('#a8a04a'), 0.35 * W.smooth(0.2, 0.45, W.fbm(x * 0.09, y * 0.09, 2, 62.0)))


# ------------------------------------------------------------------------------------------------ helpers
def _quad2(v):
    """Double-sided quad (for thin parts drawn with back-face culling)."""
    return [(0, 1, 2, 3), (3, 2, 1, 0)]


def part(W, name, loc, rz=0.0, parent=None):
    W.PARTS[name] = dict(loc=Vector(loc), rz=rz, parent=parent)


def bobj(W, x, y):
    return f'Build_{W.chunk_of(x, y)}'


def solid(W, obj, verts, faces, M, color, jitter=0.04):
    W.emit(obj, 'Ruin', verts, faces, M, color, jitter)


# ------------------------------------------------------------------------------------------------ crops
def wheat_tuft(W, obj, x, y, z, variety, stubble=False):
    R = W.R
    stalk, head = (W.hexc(c) for c in WHEAT[variety])
    v, f, uv_w = [], [], []
    cols = []
    ph = R.random()
    for k in range(3):
        bx, by = x + R.uniform(-0.22, 0.22), y + R.uniform(-0.22, 0.22)
        if stubble:
            h = R.uniform(0.12, 0.2)
            a = R.uniform(0, 6.3)
            px, py = -math.sin(a) * 0.02, math.cos(a) * 0.02
            b = len(v)
            v += [Vector((bx - px, by - py, z)), Vector((bx + px, by + py, z)), Vector((bx, by, z + h))]
            f.append((b, b + 1, b + 2))
            cols.append(W.shade(stalk, 0.85))
            uv_w += [0, 0, 0]
            continue
        h = R.uniform(1.05, 1.45)
        lean = Vector((R.uniform(-0.12, 0.12), R.uniform(-0.12, 0.12), 0))
        a = R.uniform(0, 6.3)
        perp = Vector((-math.sin(a), math.cos(a), 0))
        base = Vector((bx, by, z))
        top = base + lean + Vector((0, 0, h * 0.8))
        b = len(v)
        v += [base - perp * 0.022, base + perp * 0.022, top]
        f.append((b, b + 1, b + 2))
        cols.append(stalk)
        uv_w += [0.0, 0.0, 0.8 ** 1.5]
        # grain head: a slim drooping diamond
        d = (lean * 0.6 + Vector((0, 0, 1))).normalized()
        tip = top + d * 0.24 + lean.normalized() * 0.03 if lean.length > 0 else top + d * 0.24
        mid = top + d * 0.11
        b = len(v)
        v += [top, mid - perp * 0.04, tip, mid + perp * 0.04]
        f += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
        cols += [head, W.shade(head, 0.88)]
        uv_w += [0.8 ** 1.5, 0.9 ** 1.5, 1.0, 0.9 ** 1.5]
    a = W.acc(obj)
    base_i = len(a.v)
    a.v.extend(v)
    a.uv.extend((w, ph) for w in uv_w)
    for i, face in enumerate(f):
        a.f.append(tuple(base_i + k for k in face))
        a.fc.append(W.jit(cols[i], 0.06))
        a.fm.append('Wheat')
    return len(f)


def wheat_field(W, fi):
    f = FIELDS[fi]
    fx, fy, w, l, ang, crop, variety = f
    R = W.R
    n = 0
    sp = 0.72
    rx = w if crop == 'wheat_round' else w / 2
    ry = w if crop == 'wheat_round' else l / 2
    i = -rx
    while i <= rx:
        j = -ry
        while j <= ry:
            lx, ly = i + R.uniform(-0.3, 0.3), j + R.uniform(-0.3, 0.3)
            j += sp
            if crop == 'wheat_round':
                rr = math.hypot(lx, ly)
                if rr > w - 0.3 or abs(rr - w * 0.5) < 0.7 or abs(rr - (w - 0.9)) < 0.5 or rr < 1.6:
                    continue   # wheel tracks of the pivot irrigator, centre tower
                x, y = fx + lx, fy + ly
            else:
                if abs(lx) > w / 2 - 0.3 or abs(ly) > l / 2 - 0.3:
                    continue
                c, s = math.cos(ang), math.sin(ang)
                x, y = fx + lx * c - ly * s, fy + lx * s + ly * c
            if crop == 'wheat' and fi == 3 and ly < -l / 2 + l * HARVESTED:
                if R.random() < 0.5:
                    n += wheat_tuft(W, f'Wheat_{W.chunk_of(x, y)}', x, y, W.ground(x, y) - 0.02, variety, True)
                continue
            n += wheat_tuft(W, f'Wheat_{W.chunk_of(x, y)}', x, y, W.ground(x, y) - 0.05, variety)
        i += sp
    W.EXCL.append((fx, fy, max(w, l) * 0.5 + 1.0 if crop != 'wheat_round' else w + 1.0))
    return n


def row_crops(W, fi):
    fx, fy, w, l, ang, crop, _ = FIELDS[fi]
    R = W.R
    C = W.C
    c, s = math.cos(ang), math.sin(ang)
    row = 1.25
    lx = -w / 2 + 0.8
    count = 0
    while lx < w / 2 - 0.5:
        ly = -l / 2 + 0.6
        while ly < l / 2 - 0.5:
            x, y = fx + lx * c - ly * s, fy + lx * s + ly * c
            z = W.ground(x, y)
            obj = f'Crop_{W.chunk_of(x, y)}'
            ph = R.random()
            if crop == 'bulbroot':
                bv, bf = W.prim_ico(0)
                r_ = R.uniform(0.18, 0.28)
                W.emit(obj, 'Flora', bv, bf, W.mat_at(x, y, z + r_ * 0.3, R.uniform(0, 6), r_, (0, 0), (1, 1, 0.85)),
                       lambda fi_, cen, nn: W.hexc('#7a3a8a') if nn.z > 0.2 else W.hexc('#5a2a6a'), 0.08)
                for k in range(3):
                    v, f = W.prim_blade(R.uniform(0.4, 0.6), 0.1, 0.5)
                    W.emit(obj, 'Flora', v, f, W.mat_at(x, y, z + r_ * 0.5, k * 2.1 + R.uniform(-.3, .3)),
                           C['teal'], 0.08, 0.5, ph)
            else:   # blue kale rosette
                for k in range(5):
                    v, f = W.prim_blade(R.uniform(0.35, 0.5), 0.16, 0.4, 3, 0.5)
                    W.emit(obj, 'Flora', v, f, W.mat_at(x, y, z, k * 1.26 + R.uniform(-.2, .2), 1.0,
                                                        (0, R.uniform(-0.6, -0.3))),
                           lambda fi_, cen, nn: W.hexc('#4a78a8') if fi_ % 2 else W.hexc('#6a9ac0'), 0.06, 0.4, ph)
            count += 1
            ly += 0.85
        lx += row
    W.EXCL.append((fx, fy, max(w, l) * 0.5 + 1.0))
    return count


def fence(W, a, b, gap=None):
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    n = max(1, int(L / 2.4))
    rz = math.atan2(d.y, d.x)
    wood = W.hexc('#6a4a32')
    for k in range(n + 1):
        p = a + d * (k / n)
        if gap and abs((p - Vector(gap)).length) < 2.0:
            continue
        z = W.ground(p.x, p.y)
        v, f = W.prim_box(0.14, 0.14, 1.15)
        solid(W, bobj(W, p.x, p.y), v, f, W.mat_at(p.x, p.y, z - 0.1, rz + W.R.uniform(-.1, .1), 1.0,
                                                   (W.R.uniform(-.06, .06), 0)), wood)
        if k < n:
            q = a + d * ((k + 0.5) / n)
            if gap and abs((q - Vector(gap)).length) < 2.0:
                continue
            zq = (z + W.ground((a + d * ((k + 1) / n)).x, (a + d * ((k + 1) / n)).y)) / 2
            for hgt in (0.45, 0.85):
                v, f = W.prim_box(L / n + 0.1, 0.07, 0.09)
                solid(W, f'Deco_{W.chunk_of(q.x, q.y)}', v, f, W.mat_at(q.x, q.y, zq + hgt, rz), W.shade(wood, 1.1))


# ------------------------------------------------------------------------------------------------ buildings
ADOBE = '#e8dcc4'
THATCH = ('#c8643c', '#b45434')
BANNER = '#2f6f7a'
GOLD = '#e2b84a'
WINDOW = '#ffcf7a'


def farmhouse(W, x, y, face, r=4.0, rng_roof=0):
    obj = bobj(W, x, y)
    R = W.R
    z = W.min_ground(x, y, r) - 0.2
    M = W.mat_at(x, y, z, face)
    v, f = W.prim_cyl(10, r + 0.3, r + 0.3, 0.6, True)
    solid(W, obj, v, f, M, W.hexc('#8a7a68'))
    v, f = W.prim_cyl(10, r, r * 0.97, 3.4, False)
    solid(W, obj, [p + Vector((0, 0, 0.5)) for p in v], f, M,
          lambda fi, cen, nn: W.hexc('#d4c6aa') if fi % 5 == 0 else W.hexc(ADOBE))
    # layered thatch dome with a wide overhang
    path = [(Vector((0, 0, 3.6)), r + 1.0), (Vector((0, 0, 4.1)), r * 0.92), (Vector((0, 0, 5.1)), r * 0.62),
            (Vector((0, 0, 5.9)), r * 0.28), (Vector((0, 0, 6.2)), 0.0)]
    v, f = W.prim_tube(path, 10, False, False, twist=0.0)
    solid(W, obj, v, f + [tuple(range(9, -1, -1))], M,
          lambda fi, cen, nn: W.hexc(THATCH[(fi // 10) % 2]) if nn.z > -0.5 else W.hexc('#6a4a2a'))
    # chimney
    v, f = W.prim_box(0.7, 0.7, 2.4, 0.85)
    solid(W, obj, v, f, M @ Matrix.Translation((r * 0.45, r * 0.3, 4.2)), W.hexc('#8a6a54'))
    v, f = W.prim_box(0.9, 0.9, 0.2)
    solid(W, obj, v, f, M @ Matrix.Translation((r * 0.45, r * 0.3, 6.6)), W.hexc('#5a4a40'))
    # door (local -Y is the front), frame, porch awning on posts, bench
    v, f = W.prim_box(1.2, 0.3, 2.2)
    solid(W, obj, v, f, M @ Matrix.Translation((0, -r + 0.05, 0.55)), W.hexc('#4a3424'))
    v, f = W.prim_box(1.6, 0.25, 0.25)
    solid(W, obj, v, f, M @ Matrix.Translation((0, -r - 0.05, 2.75)), W.hexc('#7a5a3e'))
    aw = [Vector((-2.2, -r + 0.1, 3.3)), Vector((2.2, -r + 0.1, 3.3)), Vector((2.2, -r - 2.4, 2.6)),
          Vector((-2.2, -r - 2.4, 2.6))]
    W.emit(obj, 'Ruin', aw, _quad2(aw), M, W.hexc('#d8783c'), 0.03)
    banner(W, obj, M, Vector((-2.6, -r * 0.93, 1.2)), -0.55)
    for sx in (-2.0, 2.0):
        v, f = W.prim_box(0.16, 0.16, 2.2)
        solid(W, obj, v, f, M @ Matrix.Translation((sx, -r - 2.2, 0.4)), W.hexc('#6a4a32'))
    v, f = W.prim_box(1.6, 0.45, 0.45)
    solid(W, f'Deco_{W.chunk_of(x, y)}', v, f, M @ Matrix.Translation((-2.8, -r - 0.6, 0.55)), W.hexc('#7a5a3e'))
    # round glowing windows
    for k, a in enumerate((-0.9, 0.9, 2.4, -2.4)):
        p = Vector((math.sin(a) * (r + 0.02), -math.cos(a) * (r + 0.02), 2.3))
        n = Vector((math.sin(a), -math.cos(a), 0))
        right = Vector((0, 0, 1)).cross(n).normalized()
        wv = [p + n * 0.03]
        for j in range(8):
            t = 2 * math.pi * j / 8
            wv.append(p + right * math.cos(t) * 0.45 + Vector((0, 0, math.sin(t) * 0.45)))
        wf = [(0, 1 + j, 1 + (j + 1) % 8) for j in range(8)]
        wf = [(a_, c_, b_) for a_, b_, c_ in wf] if (right.cross(Vector((0, 0, 1))).dot(n) < 0) else wf
        W.emit(f'Deco_{W.chunk_of(x, y)}', 'Glow', wv, wf + [(a_, c_, b_) for a_, b_, c_ in wf], M, W.hexc(WINDOW), 0.05)
    # small side pod room
    v, f = W.prim_ico(1)
    v = [p for p in v]
    solid(W, obj, v, f, M @ Matrix.Translation((r + 1.4, 1.0, 0.6)) @ Matrix.Diagonal((2.0, 2.0, 1.7, 1.0)),
          lambda fi, cen, nn: W.hexc(ADOBE) if nn.z < 0.6 else W.hexc(THATCH[0]))
    W.EXCL.append((x, y, r + 3.0))
    return z


def barn(W, x, y, face, L=13.0, Wd=7.5):
    obj = bobj(W, x, y)
    z = W.min_ground(x, y, L * 0.5) - 0.3
    M = W.mat_at(x, y, z, face)
    v, f = W.prim_box(Wd, L, 3.2)
    solid(W, obj, [p + Vector((0, 0, 0.3)) for p in v], f, M,
          lambda fi, cen, nn: W.hexc('#e8dcc4') if abs(nn.x) > 0.5 else W.hexc('#dccfb4'))
    # vaulted roof: half-cylinder of ribbed panels along the length
    segs = 7
    rings = []
    for k in range(segs + 1):
        a = math.pi * k / segs
        rings.append((math.cos(a) * (Wd / 2 + 0.4), math.sin(a) * (Wd / 2 + 0.2) * 0.8 + 3.4))
    verts, faces = [], []
    for side in (-1, 1):
        for (px, pz) in rings:
            verts.append(Vector((px, side * (L / 2 + 0.5), pz)))
    for k in range(segs):
        a, b = k, k + 1
        faces.append((a, b, segs + 1 + b, segs + 1 + a))
        faces.append((segs + 1 + a, segs + 1 + b, b, a))
    solid(W, obj, verts, faces, M, lambda fi, cen, nn: W.hexc('#c8643c') if (fi // 2) % 2 else W.hexc('#b45434'))
    for side in (-1, 1):   # gable walls
        gv = [Vector((0, side * L / 2, 3.4))] + [Vector((px, side * L / 2, pz)) for px, pz in rings]
        gf = [(0, k + 1, k + 2) for k in range(segs)]
        gf2 = [(a_, c_, b_) for a_, b_, c_ in gf]
        solid(W, obj, gv, gf + gf2, M, W.hexc('#e2d6bc'))
    for ry in (-L / 2 + 0.5, 0.0, L / 2 - 0.5):   # roof ribs
        rv = [Vector((px * 1.03, ry, pz + 0.08)) for px, pz in rings]
        path = [(p, 0.12) for p in rv]
        v, f = W.prim_tube(path, 4, False, False)
        solid(W, obj, v, f, M, W.hexc('#5a3424'))
    v, f = W.prim_box(3.6, 0.3, 3.0)   # big doors
    solid(W, obj, v, f, M @ Matrix.Translation((0, -L / 2 - 0.05, 0.3)), W.hexc('#4a3424'))
    v, f = W.prim_box(0.12, 0.32, 3.0)
    solid(W, obj, v, f, M @ Matrix.Translation((0, -L / 2 - 0.1, 0.3)), W.hexc('#2a2018'))
    banner(W, obj, M, Vector((-Wd / 2 - 0.05, -2.0, 0.8)), math.pi / 2)
    banner(W, obj, M, Vector((-Wd / 2 - 0.05, 2.5, 0.8)), math.pi / 2)
    W.EXCL.append((x, y, L * 0.6 + 2.0))
    return M


def silo(W, x, y, h=9.0, r=1.8):
    obj = bobj(W, x, y)
    z = W.min_ground(x, y, r) - 0.3
    M = W.mat_at(x, y, z)
    v, f = W.prim_cyl(10, r, r, h, False)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#ece2cc') if (int(cen.z / 1.5) % 4) else W.hexc('#b8aa90'))
    path = [(Vector((0, 0, h)), r + 0.2), (Vector((0, 0, h + 1.0)), r * 0.75), (Vector((0, 0, h + 1.7)), r * 0.3),
            (Vector((0, 0, h + 1.9)), 0)]
    v, f = W.prim_tube(path, 10, False, False)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#c8643c') if fi % 2 else W.hexc('#b45434'))
    for k in range(int(h / 0.6)):
        v, f = W.prim_box(0.5, 0.06, 0.06)
        solid(W, f'Deco_{W.chunk_of(x, y)}', v, f, M @ Matrix.Translation((0, -r - 0.15, 0.4 + k * 0.6)), W.hexc('#6a6a70'))
    W.EXCL.append((x, y, r + 1.0))


def water_tower(W, x, y):
    obj = bobj(W, x, y)
    z = W.min_ground(x, y, 2.0) - 0.2
    M = W.mat_at(x, y, z, 0.4)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        path = [(Vector((sx * 1.6, sy * 1.6, 0)), 0.14), (Vector((sx * 1.0, sy * 1.0, 6.0)), 0.12)]
        v, f = W.prim_tube(path, 4, True)
        solid(W, obj, v, f, M, W.hexc('#6a5a4a'))
    v, f = W.prim_ico(1)
    solid(W, obj, v, f, M @ Matrix.Translation((0, 0, 7.4)) @ Matrix.Diagonal((2.0, 2.0, 1.6, 1)),
          lambda fi, cen, nn: W.hexc('#c8913c') if nn.z > -0.2 else W.hexc('#a87430'))
    W.EXCL.append((x, y, 3.0))


def greenhouse(W, x, y, r=4.2):
    obj = bobj(W, x, y)
    z = W.min_ground(x, y, r) - 0.2
    M = W.mat_at(x, y, z)
    v, f = W.prim_cyl(12, r + 0.2, r + 0.2, 0.5, True)
    solid(W, obj, v, f, M, W.hexc('#8a7a68'))
    v, f = W.prim_ico(1)
    keep = [fc for fc in f if sum(v[k].z for k in fc) / 3 > -0.05]
    vv = [p * r + Vector((0, 0, 0.45)) for p in v]
    vv = [Vector((p.x, p.y, max(p.z, 0.45))) for p in vv]
    W.emit(f'Deco_{W.chunk_of(x, y)}', 'Glow', vv, keep, M,
           lambda fi, cen, nn: W.hexc('#4fb8a8') if fi % 4 else W.hexc('#d8f0e0'), 0.06)
    W.EXCL.append((x, y, r + 1.5))


def storage_pods(W, x, y, n=3):
    for k in range(n):
        a = k * 2.1 + 0.3
        px, py = x + math.cos(a) * 2.4, y + math.sin(a) * 2.4
        v, f = W.prim_ico(1)
        z = W.ground(px, py) - 0.2
        solid(W, bobj(W, px, py), v, f, W.mat_at(px, py, z, 0, 1.4, (0, 0), (1, 1, 0.9)),
              lambda fi, cen, nn: W.hexc('#c8913c') if nn.z > 0.3 else W.hexc('#a8a294'))
    W.EXCL.append((x, y, 4.5))


def hay_bales(W, x, y, n=5):
    for k in range(n):
        px, py = x + W.R.uniform(-2.5, 2.5), y + W.R.uniform(-2.5, 2.5)
        v, f = W.prim_cyl(8, 0.6, 0.6, 1.2, True, True)
        M = W.mat_at(px, py, W.ground(px, py) + 0.55, W.R.uniform(0, 3.1), 1.0, (math.pi / 2, 0))
        W.emit(f'Deco_{W.chunk_of(px, py)}', 'Ruin', [p - Vector((0, 0, 0.6)) for p in v], f, M,
               lambda fi, cen, nn: W.hexc('#d8b04a') if fi < 8 else W.hexc('#c09a3a'), 0.08)
    W.EXCL.append((x, y, 3.5))


def cart(W, x, y, face):
    obj = f'Deco_{W.chunk_of(x, y)}'
    z = W.ground(x, y)
    M = W.mat_at(x, y, z, face)
    v, f = W.prim_box(1.6, 2.6, 0.6)
    W.emit(obj, 'Ruin', v, f, M @ Matrix.Translation((0, 0, 0.7)), W.hexc('#7a5a3e'))
    for sx in (-0.95, 0.95):
        v, f = W.prim_cyl(10, 0.65, 0.65, 0.15, True, True)
        W.emit(obj, 'Ruin', v, f, M @ Matrix.Translation((sx, 0, 0.65)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'),
               W.hexc('#5a4030'))
    for k in range(3):
        v, f = W.prim_ico(0)
        W.emit(obj, 'Ruin', v, f, M @ Matrix.Translation((W.R.uniform(-.4, .4), W.R.uniform(-.8, .8), 1.2)) @
               Matrix.Scale(0.3, 4), W.hexc('#7a3a8a'))


def well(W, x, y):
    obj = bobj(W, x, y)
    z = W.ground(x, y) - 0.1
    M = W.mat_at(x, y, z)
    v, f = W.prim_cyl(8, 1.0, 1.0, 0.9, True)
    solid(W, obj, v, f, M, W.hexc('#9a8a76'))
    for sx in (-0.9, 0.9):
        v, f = W.prim_box(0.14, 0.14, 2.2)
        solid(W, obj, v, f, M @ Matrix.Translation((sx, 0, 0.5)), W.hexc('#6a4a32'))
    rv = [Vector((-1.3, -0.9, 2.4)), Vector((1.3, -0.9, 2.4)), Vector((1.3, 0.0, 2.9)), Vector((-1.3, 0.0, 2.9))]
    W.emit(obj, 'Ruin', rv, _quad2(rv), M, W.hexc('#9a4a32'))
    rv = [Vector((-1.3, 0.0, 2.9)), Vector((1.3, 0.0, 2.9)), Vector((1.3, 0.9, 2.4)), Vector((-1.3, 0.9, 2.4))]
    W.emit(obj, 'Ruin', rv, _quad2(rv), M, W.hexc('#86402c'))
    W.EXCL.append((x, y, 1.8))


def condenser_spire(W, x, y, h=11.0):
    """Moisture condenser: a slender finned spire with a glowing collector at the top."""
    obj = bobj(W, x, y)
    z = W.ground(x, y) - 0.3
    M = W.mat_at(x, y, z, W.R.uniform(0, 3))
    path = [(Vector((0, 0, 0)), 0.9), (Vector((0, 0, 1.2)), 0.55), (Vector((0, 0, h * 0.7)), 0.28),
            (Vector((0, 0, h)), 0.18)]
    v, f = W.prim_tube(path, 6, True)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#d8d0c0') if (fi // 6) % 2 else W.hexc('#a8a294'))
    for k in range(4):   # fins
        a = k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        fv = [Vector((0, 0, 1.5)) + d * 0.3, Vector((0, 0, 1.5)) + d * 1.2, Vector((0, 0, h * 0.6)) + d * 0.5,
              Vector((0, 0, h * 0.75)) + d * 0.25]
        solid(W, obj, fv, _quad2(fv), M, W.hexc('#2f7f7a'))
    v, f = W.prim_ico(1)
    W.emit(f'Deco_{W.chunk_of(x, y)}', 'Glow', v, f, M @ Matrix.Translation((0, 0, h + 0.4)) @ Matrix.Diagonal((0.5, 0.5, 0.8, 1)),
           W.C['gcyan'], 0.05)
    W.EXCL.append((x, y, 1.6))


def wind_turbine(W, name, x, y, h=9.0, speed='080'):
    """Vertical-axis spiral turbine: static mast (Build) + spinning rotor object."""
    obj = bobj(W, x, y)
    z = W.ground(x, y) - 0.2
    M = W.mat_at(x, y, z)
    v, f = W.prim_cyl(6, 0.9, 0.7, 1.0, True)
    solid(W, obj, v, f, M, W.hexc('#8a7a68'))
    v, f = W.prim_cyl(6, 0.22, 0.16, h + 0.8, True)
    solid(W, obj, v, f, M, W.hexc('#d8d0c0'))
    rot = f'Spin_y_{speed}_{name}'
    hub_z = 2.0
    blade_h = h - 2.2
    for b in range(3):
        verts, faces = [], []
        steps = 8
        for k in range(steps + 1):
            t = k / steps
            a = b * 2 * math.pi / 3 + t * math.pi * 0.9
            r_ = 1.3 * math.sin(math.pi * (0.1 + 0.8 * t)) + 0.25
            c = Vector((math.cos(a) * r_, math.sin(a) * r_, t * blade_h))
            tang = Vector((-math.sin(a), math.cos(a), 0)) * 0.35
            verts += [c - tang, c + tang]
        for k in range(steps):
            i = k * 2
            faces += [(i, i + 1, i + 3, i + 2), (i + 2, i + 3, i + 1, i)]
        W.emit(rot, 'Ruin', verts, faces, Matrix.Identity(4),
               lambda fi, cen, nn: W.hexc('#e8e4dc') if (fi // 2) % 4 else W.hexc('#2f7f7a'), 0.03)
    part(W, rot, (x, y, z + hub_z))
    W.EXCL.append((x, y, 2.0))


# ------------------------------------------------------------------------------------------------ machinery
def hover_harvester(W, x, y, face, travel=16):
    """Hovering combine: hull, glass cab, grain hopper, glowing lift pads; the reel is a spinning child."""
    name = f'Mover_{travel}_harvester'
    hull = W.hexc('#e0d6c0')
    accent = W.hexc('#d8664a')
    z = W.ground(x, y) + 0.9
    I = Matrix.Identity(4)
    v, f = W.prim_box(4.4, 2.8, 1.5, 0.85)
    W.emit(name, 'Ruin', [p + Vector((0, 0, 0)) for p in v], f, I,
           lambda fi, cen, nn: accent if fi in (2, 4) else hull, 0.03)
    v, f = W.prim_box(2.2, 2.4, 1.6, 0.7)   # grain hopper at the back
    W.emit(name, 'Ruin', v, f, Matrix.Translation((-1.2, 0, 1.4)), W.hexc('#c8913c'), 0.03)
    v, f = W.prim_ico(1)   # glass cab, front-top
    keep = [fc for fc in f if sum(v[k].z for k in fc) / 3 > -0.1]
    W.emit(name, 'Glow', [p * 1.0 + Vector((1.2, 0, 1.4)) for p in v], keep, Matrix.Diagonal((1.0, 1.0, 0.9, 1)),
           lambda fi, cen, nn: W.hexc('#3a8a88') if fi % 3 else W.hexc('#9ae0d8'), 0.03)
    for sx, sy in ((-1.6, -1.1), (-1.6, 1.1), (1.5, -1.1), (1.5, 1.1)):   # lift pads
        v, f = W.prim_cyl(8, 0.55, 0.45, 0.25, True, True)
        W.emit(name, 'Ruin', v, f, Matrix.Translation((sx, sy, -0.3)), W.hexc('#5a5a64'), 0.03)
        v, f = W.prim_cyl(8, 0.4, 0.4, 0.05, False, True)
        W.emit(name, 'Glow', v, f, Matrix.Translation((sx, sy, -0.33)), W.C['gcyan'], 0.0)
    v, f = W.prim_cyl(6, 0.18, 0.14, 1.4, True)   # exhaust stack
    W.emit(name, 'Ruin', v, f, Matrix.Translation((-2.0, 0.9, 1.0)), W.hexc('#5a5a64'), 0.03)
    # header frame in front (spans local Y)
    v, f = W.prim_box(0.6, 5.6, 0.5)
    W.emit(name, 'Ruin', v, f, Matrix.Translation((2.7, 0, -0.35)), accent, 0.03)
    for sy in (-2.75, 2.75):
        v, f = W.prim_box(1.4, 0.15, 1.2)
        W.emit(name, 'Ruin', v, f, Matrix.Translation((2.85, sy, -0.4)), accent, 0.03)
    # spinning reel (child): paddles around local Y; spins about Godot local Z (= Blender local Y)
    reel = 'Spin_z_150_reel'
    for k in range(5):
        a = k * 2 * math.pi / 5
        c = Vector((math.cos(a) * 0.55, 0, math.sin(a) * 0.55))
        v, f = W.prim_box(0.08, 5.2, 0.5)
        W.emit(reel, 'Ruin', [p + Vector((0, 0, -0.25)) for p in v], f,
               Matrix.Translation(c) @ Matrix.Rotation(-a, 4, 'Y'), W.hexc('#e8e4dc'), 0.03)
    v, f = W.prim_cyl(6, 0.12, 0.12, 5.4, True, True)
    W.emit(reel, 'Ruin', [p - Vector((0, 0, 2.7)) for p in v], f, Matrix.Rotation(math.pi / 2, 4, 'X'),
           W.hexc('#5a5a64'), 0.03)
    part(W, name, (x, y, z), face)
    part(W, reel, (3.2, 0, 0.35), 0.0, parent=name)


def pivot_irrigator(W, fi):
    fx, fy, r = FIELDS[fi][0], FIELDS[fi][1], FIELDS[fi][2]
    z = W.ground(fx, fy) - 0.2
    obj = bobj(W, fx, fy)
    M = W.mat_at(fx, fy, z)
    v, f = W.prim_cyl(6, 0.9, 0.6, 4.2, True)
    solid(W, obj, v, f, M, W.hexc('#a8a294'))
    v, f = W.prim_ico(1)
    W.emit(f'Deco_{W.chunk_of(fx, fy)}', 'Glow', v, f, M @ Matrix.Translation((0, 0, 4.5)) @ Matrix.Scale(0.45, 4),
           W.C['gcyan'], 0.05)
    arm = 'Spin_y_006_pivot'
    L = r - 0.3
    pipe = [(Vector((0.4, 0, 3.4)), 0.14), (Vector((L, 0, 3.0)), 0.12)]
    v, f = W.prim_tube(pipe, 5, True, True)
    W.emit(arm, 'Ruin', v, f, Matrix.Identity(4), W.hexc('#d8d0c0'), 0.03)
    for k in range(1, 9):   # truss chords
        t = k / 9
        p = Vector((0.4 + (L - 0.4) * t, 0, 3.3 - 0.4 * t))
        v, f = W.prim_tube([(p, 0.04), (p + Vector((0.6, 0, 0.7)), 0.04)], 3, False)
        W.emit(arm, 'Ruin', v, f, Matrix.Identity(4), W.hexc('#9a9aa4'), 0.03)
        v, f = W.prim_tube([(p + Vector((0, 0, -0.1)), 0.06), (p + Vector((0, 0, -0.45)), 0.0)], 4, False)
        W.emit(arm, 'Glow', v, f, Matrix.Identity(4), W.C['gcyan'], 0.03)
    for rr in (r * 0.5, L - 0.2):   # A-frame towers with ball wheels on the wheel tracks
        gz = W.ground(fx + rr, fy) - z
        for sy in (-0.9, 0.9):
            v, f = W.prim_tube([(Vector((rr, sy, gz + 0.5)), 0.07), (Vector((rr, 0, 3.2)), 0.07)], 4, True)
            W.emit(arm, 'Ruin', v, f, Matrix.Identity(4), W.hexc('#9a9aa4'), 0.03)
            v, f = W.prim_ico(1)
            W.emit(arm, 'Ruin', v, f, Matrix.Translation((rr, sy, gz + 0.45)) @ Matrix.Scale(0.45, 4),
                   W.hexc('#3a3a42'), 0.03)
    part(W, arm, (fx, fy, z))


def seeder_drone(W, name, x, y, face, travel=12):
    nm = f'Mover_{travel}_{name}'
    z = W.ground(x, y) + 2.6
    v, f = W.prim_ico(1)
    W.emit(nm, 'Ruin', v, f, Matrix.Diagonal((0.75, 0.75, 0.28, 1)),
           lambda fi, cen, nn: W.hexc('#e8e4dc') if nn.z > 0 else W.hexc('#5a5a64'), 0.03)
    v, f = W.prim_cyl(10, 0.5, 0.5, 0.05, False, True)
    W.emit(nm, 'Glow', v, f, Matrix.Translation((0, 0, -0.22)), W.C['glime'], 0.0)
    v, f = W.prim_tube([(Vector((0, 0, 0.2)), 0.03), (Vector((0, 0, 0.6)), 0.0)], 3, False)
    W.emit(nm, 'Ruin', v, f, Matrix.Identity(4), W.hexc('#5a5a64'), 0.03)
    part(W, nm, (x, y, z), face)


def crawler_tractor(W, x, y, face):
    obj = bobj(W, x, y)
    z = W.ground(x, y)
    M = W.mat_at(x, y, z, face)
    body = W.hexc('#2f7f7a')
    v, f = W.prim_box(3.4, 1.8, 1.1, 0.85)
    solid(W, obj, v, f, M @ Matrix.Translation((0, 0, 1.0)), body)
    v, f = W.prim_ico(1)
    keep = [fc for fc in f if sum(v[k].z for k in fc) / 3 > -0.1]
    W.emit(f'Deco_{W.chunk_of(x, y)}', 'Glow', v, keep, M @ Matrix.Translation((-0.4, 0, 2.05)) @
           Matrix.Diagonal((0.9, 0.8, 0.8, 1)), lambda fi, cen, nn: W.hexc('#3a8a88') if fi % 3 else W.hexc('#9ae0d8'))
    for sx in (-1.15, 1.15):   # four big spherical wheels
        for sy in (-1.05, 1.05):
            v, f = W.prim_ico(1)
            solid(W, obj, v, f, M @ Matrix.Translation((sx, sy, 0.62)) @ Matrix.Diagonal((0.62, 0.42, 0.62, 1)),
                  lambda fi, cen, nn: W.hexc('#3a3a42') if fi % 2 else W.hexc('#26262c'))
    for k in range(4):   # plough tines behind
        v, f = W.prim_tube([(Vector((-1.9, -0.75 + k * 0.5, 0.9)), 0.07), (Vector((-2.5, -0.75 + k * 0.5, 0.1)), 0.0)], 4, False)
        solid(W, obj, v, f, M, W.hexc('#8a909a'))
    v, f = W.prim_ico(0)
    W.emit(f'Deco_{W.chunk_of(x, y)}', 'Glow', v, f, M @ Matrix.Translation((1.75, 0, 1.2)) @ Matrix.Scale(0.18, 4),
           W.hexc('#ffcf7a'))
    W.EXCL.append((x, y, 3.0))


def banner(W, obj, M, p, rz):
    """Hanging teal cloth banner with a golden sun emblem (the valley's farming guild)."""
    Mb = M @ Matrix.Translation(p) @ Matrix.Rotation(rz, 4, 'Z')
    bv = [Vector((-0.6, -0.06, 2.6)), Vector((0.6, -0.06, 2.6)), Vector((0.6, -0.06, 0.4)), Vector((0, -0.06, 0.0)),
          Vector((-0.6, -0.06, 0.4))]
    W.emit(f'Deco_{W.chunk_of(Mb.translation.x, Mb.translation.y)}', 'Ruin', bv, [(0, 1, 2, 3, 4), (4, 3, 2, 1, 0)], Mb,
           W.hexc(BANNER), 0.02)
    ev = [Vector((0, -0.09, 1.55))]
    for k in range(8):
        a = 2 * math.pi * k / 8
        ev.append(Vector((math.cos(a) * 0.34, -0.09, 1.55 + math.sin(a) * 0.34)))
    ef = [(0, 1 + k, 1 + (k + 1) % 8) for k in range(8)]
    W.emit(f'Deco_{W.chunk_of(Mb.translation.x, Mb.translation.y)}', 'Ruin', ev, ef + [(a_, c_, b_) for a_, b_, c_ in ef],
           Mb, W.hexc(GOLD), 0.02)


def farm_hall(W, x, y, face, L=16.0, D=8.0):
    """Main farm hall: cream plaster, terracotta hip roof, an arcade porch, banners and a domed tower."""
    obj = bobj(W, x, y)
    z = W.min_ground(x, y, L * 0.5) - 0.3
    M = W.mat_at(x, y, z, face)
    v, f = W.prim_box(L, D, 4.2)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#e8dcc4') if fi != 1 else W.hexc('#d8cab0'))
    v, f = W.prim_box(L + 0.3, D + 0.3, 0.5)
    solid(W, obj, v, f, M, W.hexc('#a89680'))
    # hip roof with overhang
    rv = [Vector((-L / 2 - 1.0, -D / 2 - 1.0, 4.2)), Vector((L / 2 + 1.0, -D / 2 - 1.0, 4.2)),
          Vector((L / 2 + 1.0, D / 2 + 1.0, 4.2)), Vector((-L / 2 - 1.0, D / 2 + 1.0, 4.2)),
          Vector((-L / 2 + D / 2, 0, 7.0)), Vector((L / 2 - D / 2, 0, 7.0))]
    rf = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (3, 2, 1, 0)]
    solid(W, obj, rv, rf, M, lambda fi, cen, nn: W.hexc(THATCH[fi % 2]) if nn.z > 0 else W.hexc('#7a4a30'))
    # arcade porch along the front
    pv = [Vector((-L / 2, -D / 2, 3.5)), Vector((L / 2, -D / 2, 3.5)), Vector((L / 2, -D / 2 - 3.0, 2.9)),
          Vector((-L / 2, -D / 2 - 3.0, 2.9))]
    W.emit(obj, 'Ruin', pv, _quad2(pv), M, W.hexc('#d8783c'), 0.03)
    for k in range(6):
        px = -L / 2 + 0.6 + k * (L - 1.2) / 5
        v, f = W.prim_box(0.25, 0.25, 2.8)
        solid(W, obj, v, f, M @ Matrix.Translation((px, -D / 2 - 2.8, 0.2)), W.hexc('#7a5236'))
    v, f = W.prim_box(L, 0.2, 0.3)
    solid(W, obj, v, f, M @ Matrix.Translation((0, -D / 2 - 2.8, 2.9)), W.hexc('#7a5236'))
    # doors, windows, banners
    for px in (-4.0, 3.0):
        v, f = W.prim_box(1.4, 0.3, 2.4)
        solid(W, obj, v, f, M @ Matrix.Translation((px, -D / 2 - 0.05, 0.4)), W.hexc('#5a3a26'))
    for px in (-6.5, -1.5, 5.5):
        v, f = W.prim_box(1.2, 0.25, 1.1)
        W.emit(f'Deco_{W.chunk_of(x, y)}', 'Ruin', v, f, M @ Matrix.Translation((px, -D / 2 - 0.04, 1.5)),
               W.hexc('#7a5236'), 0.03)
        v, f = W.prim_box(0.95, 0.25, 0.85)
        W.emit(f'Deco_{W.chunk_of(x, y)}', 'Ruin', v, f, M @ Matrix.Translation((px, -D / 2 - 0.08, 1.62)),
               W.hexc('#34505e'), 0.03)
    banner(W, obj, M, Vector((-0.6, -D / 2 - 0.05, 1.0)), 0.0)
    banner(W, obj, M, Vector((7.2, -D / 2 - 0.05, 1.0)), 0.0)
    # domed tower at one end, pipe arcing to the silo
    tz = 0.0
    v, f = W.prim_cyl(10, 2.2, 2.0, 9.0, False)
    solid(W, obj, v, f, M @ Matrix.Translation((-L / 2 + 1.5, 1.0, tz)),
          lambda fi, cen, nn: W.hexc('#ece2cc') if (int(cen.z / 1.2) % 4) else W.hexc('#b8aa90'))
    path = [(Vector((0, 0, 9.0)), 2.4), (Vector((0, 0, 10.0)), 1.9), (Vector((0, 0, 10.8)), 1.0), (Vector((0, 0, 11.1)), 0)]
    v, f = W.prim_tube(path, 10, False, False)
    solid(W, obj, v, f, M @ Matrix.Translation((-L / 2 + 1.5, 1.0, tz)), lambda fi, cen, nn: W.hexc('#c8643c') if fi % 2 else W.hexc('#9a8a7a'))
    banner(W, obj, M, Vector((-L / 2 + 1.5, 1.0 - 2.15, 4.2)), 0.0)
    pipe = [Vector((-L / 2 + 1.5 + 1.8, 1.0, 7.5)), Vector((-L / 2 + 6.0, 2.0, 9.5)), Vector((-L / 2 + 9.0, 2.5, 7.2))]
    v, f = W.prim_tube([(p, 0.35) for p in pipe], 6, True, True)
    solid(W, obj, v, f, M, W.hexc('#9a9aa4'))
    W.EXCL.append((x, y, L * 0.65 + 3.0))
    return M


def hay_cubes(W, x, y, n=6, rz=0.0):
    obj = f'Deco_{W.chunk_of(x, y)}'
    z = W.ground(x, y) - 0.05
    k = 0
    for layer in range(3):
        for i in range(max(1, (n - layer * 3) // (layer + 1))):
            px = (i - 1) * 1.15 + layer * 0.55
            M = W.mat_at(x, y, z + layer * 0.72, rz) @ Matrix.Translation((px, W.R.uniform(-0.05, 0.05), 0))
            v, f = W.prim_box(1.1, 0.75, 0.72)
            W.emit(obj, 'Ruin', v, f, M, lambda fi, cen, nn: W.hexc('#e0b850') if fi % 3 else W.hexc('#c89a3c'), 0.06)
            v, f = W.prim_box(0.06, 0.78, 0.74)
            W.emit(obj, 'Ruin', v, f, M @ Matrix.Translation((0.25, 0, -0.01)), W.hexc('#8a6a3a'), 0.0)
            k += 1
    W.EXCL.append((x, y, 2.5))


def crates(W, x, y, n=3):
    obj = f'Deco_{W.chunk_of(x, y)}'
    for i in range(n):
        px, py = x + W.R.uniform(-1.2, 1.2), y + W.R.uniform(-1.2, 1.2)
        s_ = W.R.uniform(0.6, 0.9)
        M = W.mat_at(px, py, W.ground(px, py) - 0.02, W.R.uniform(0, 1.5))
        v, f = W.prim_box(s_, s_, s_)
        W.emit(obj, 'Ruin', v, f, M, W.hexc('#8a6440'), 0.06)
        v, f = W.prim_box(s_ * 1.04, s_ * 1.04, 0.08)
        W.emit(obj, 'Ruin', v, f, M @ Matrix.Translation((0, 0, s_ * 0.5)), W.hexc('#5a6a74'), 0.0)
    W.EXCL.append((x, y, 1.8))


def lavender(W, x, y):
    obj = f'Crop_{W.chunk_of(x, y)}'
    z = W.ground(x, y) - 0.05
    ph = W.R.random()
    for k in range(W.R.randint(4, 7)):
        px, py = x + W.R.uniform(-0.35, 0.35), y + W.R.uniform(-0.35, 0.35)
        h = W.R.uniform(0.45, 0.8)
        v, f = W.prim_tube([(Vector((0, 0, 0)), 0.015), (Vector((0, 0, h * 0.6)), 0.015)], 3, False)
        W.emit(obj, 'Flora', v, f, W.mat_at(px, py, z), W.hexc('#5a8a40'), 0.05, h, ph)
        v, f = W.prim_tube([(Vector((0, 0, h * 0.55)), 0.05), (Vector((0, 0, h * 0.8)), 0.045), (Vector((0, 0, h)), 0.0)], 4, False)
        W.emit(obj, 'Flora', v, f, W.mat_at(px, py, z), W.hexc('#a682ea') if k % 2 else W.hexc('#8a68d8'), 0.06, h, ph)


def bush(W, x, y, s=1.0):
    obj = f'Flora_{W.chunk_of(x, y)}'
    z = W.ground(x, y) - 0.2
    ph = W.R.random()
    for k in range(W.R.randint(3, 5)):
        v, f = W.prim_ico(1)
        r_ = W.R.uniform(0.45, 0.8) * s
        px, py = x + W.R.uniform(-0.6, 0.6) * s, y + W.R.uniform(-0.6, 0.6) * s
        W.emit(obj, 'Flora', [p * r_ for p in v], f, W.mat_at(px, py, z + r_ * 0.6),
               lambda fi, cen, nn: W.hexc('#5c9a3c') if nn.z > 0.2 else W.hexc('#3e7432'), 0.08, 2.0 * s, ph)


def acacia(W, x, y, s=1.0):
    """Flat-topped green shade tree that farmers plant along the valley edges."""
    obj = f'Flora_{W.chunk_of(x, y)}'
    z = W.ground(x, y) - 0.3
    R = W.R
    ph = R.random()
    H = R.uniform(5.0, 7.0) * s
    lean = Vector((R.uniform(-1, 1), R.uniform(-1, 1), 0)).normalized() * H * 0.18
    path = [(Vector((0, 0, H * t)) + lean * t * t, W.lerp(0.35, 0.15, t) * s) for t in (0, 0.35, 0.7, 1.0)]
    v, f = W.prim_tube(path, 5, False)
    W.emit(obj, 'Flora', v, f, W.mat_at(x, y, z), W.hexc('#6a4a36'), 0.05, H, ph)
    top = Vector((0, 0, H)) + lean
    for k in range(R.randint(3, 4)):
        a, d = R.uniform(0, 6.3), R.uniform(0.5, 1.6) * s
        c = top + Vector((math.cos(a) * d, math.sin(a) * d, R.uniform(-0.3, 0.4)))
        v, f = W.prim_ico(1)
        rr = R.uniform(1.6, 2.4) * s
        W.emit(obj, 'Flora', [Vector((p.x * rr, p.y * rr, p.z * rr * 0.38)) for p in v], f,
               W.mat_at(x + c.x, y + c.y, z + c.z), lambda fi, cen, nn: W.hexc('#5e9a3a') if nn.z > 0.3 else W.hexc('#3c6e2c'),
               0.07, 0.0001, ph)
    W.EXCL.append((x, y, 1.2))


def walker_harvester(W, x, y, face):
    """Four-legged walking harvester: white/grey hull, orange trim, cyan glow, wide spinning reel up front."""
    name = 'Build_walker'
    body = 'Mover_0_walkerbody'
    white, grey, orange = W.hexc('#e8e6e0'), W.hexc('#7a7c84'), W.hexc('#e07a3a')
    z = W.ground(x, y)
    I = Matrix.Identity(4)
    bz = 3.2
    v, f = W.prim_box(4.6, 3.0, 1.9, 0.82)
    W.emit(body, 'Ruin', [p + Vector((0, 0, -0.9)) for p in v], f, I,
           lambda fi, cen, nn: orange if fi == 2 else (white if nn.z > -0.3 else grey), 0.03)
    v, f = W.prim_box(2.4, 2.4, 1.5, 0.8)   # cab
    W.emit(body, 'Ruin', v, f, Matrix.Translation((0.9, 0, 0.95)), white, 0.03)
    gv = [Vector((2.12, -1.0, 1.45)), Vector((2.12, 1.0, 1.45)), Vector((2.12, 1.0, 2.05)), Vector((2.12, -1.0, 2.05))]
    W.emit(body, 'Glow', gv, [(0, 1, 2, 3), (3, 2, 1, 0)], I, W.hexc('#28343e'), 0.0)
    gv = [Vector((2.14, -1.0, 1.35)), Vector((2.14, 1.0, 1.35)), Vector((2.14, 1.0, 1.43)), Vector((2.14, -1.0, 1.43))]
    W.emit(body, 'Glow', gv, [(0, 1, 2, 3), (3, 2, 1, 0)], I, W.C['gcyan'], 0.0)
    v, f = W.prim_box(1.8, 2.6, 1.2, 0.85)   # grain tank
    W.emit(body, 'Ruin', v, f, Matrix.Translation((-1.5, 0, 0.95)), grey, 0.03)
    for sx in (-1, 1):   # legs: hip on the hull side, knee up and out, foot on the ground
        for sy in (-1, 1):
            hip = Vector((sx * 1.6, sy * 1.4, -0.3))
            knee = Vector((sx * 3.0, sy * 3.1, 0.9))
            foot = Vector((sx * 3.4, sy * 3.6, -bz + 0.15))
            v, f = W.prim_tube([(hip, 0.32), (knee, 0.26)], 6, True, True)
            W.emit(body, 'Ruin', v, f, I, grey, 0.03)
            v, f = W.prim_tube([(knee, 0.24), (foot, 0.16)], 6, True, True)
            W.emit(body, 'Ruin', v, f, I, white, 0.03)
            v, f = W.prim_ico(1)
            W.emit(body, 'Ruin', [p * 0.38 + knee for p in v], f, I, orange, 0.03)
            v, f = W.prim_cyl(6, 0.45, 0.35, 0.3, True, True)
            W.emit(body, 'Ruin', v, f, Matrix.Translation(foot - Vector((0, 0, 0.15))), W.hexc('#4a4c54'), 0.03)
    v, f = W.prim_box(0.6, 7.0, 0.5)   # header frame
    W.emit(body, 'Ruin', v, f, Matrix.Translation((3.2, 0, -2.3)), orange, 0.03)
    for sy in (-3.5, 3.5):
        v, f = W.prim_box(1.6, 0.15, 1.3)
        W.emit(body, 'Ruin', v, f, Matrix.Translation((3.4, sy, -2.6)), grey, 0.03)
    for sy in (-1.2, 1.2):
        v, f = W.prim_tube([(Vector((1.8, sy, -0.8)), 0.14), (Vector((3.1, sy, -2.0)), 0.12)], 5, True, True)
        W.emit(body, 'Ruin', v, f, I, grey, 0.03)
    reel = 'Spin_z_120_walkerreel'
    for k in range(6):
        a = k * 2 * math.pi / 6
        c = Vector((math.cos(a) * 0.6, 0, math.sin(a) * 0.6))
        v, f = W.prim_box(0.08, 6.6, 0.45)
        W.emit(reel, 'Ruin', [p + Vector((0, 0, -0.22)) for p in v], f,
               Matrix.Translation(c) @ Matrix.Rotation(-a, 4, 'Y'), W.hexc('#e8e4dc'), 0.03)
    part(W, body, (x, y, z + bz), face)
    part(W, reel, (3.7, 0, -2.0), 0.0, parent=body)
    W.EXCL.append((x, y, 4.0))


def hauler(W, x, y, face):
    """Cargo hauler: chunky four-wheeled flatbed loaded with hay cubes, cyan headlights."""
    obj = bobj(W, x, y)
    deco = f'Deco_{W.chunk_of(x, y)}'
    z = W.ground(x, y)
    M = W.mat_at(x, y, z, face)
    white, grey, orange = W.hexc('#e8e6e0'), W.hexc('#6a6c74'), W.hexc('#e07a3a')
    v, f = W.prim_box(4.2, 2.1, 0.7)
    solid(W, obj, v, f, M @ Matrix.Translation((0, 0, 0.7)), lambda fi, cen, nn: orange if fi in (2, 4) else white)
    v, f = W.prim_box(1.4, 2.0, 1.2, 0.85)
    solid(W, obj, v, f, M @ Matrix.Translation((1.4, 0, 1.4)), white)
    gv = [Vector((2.12, -0.8, 1.7)), Vector((2.12, 0.8, 1.7)), Vector((2.12, 0.8, 2.3)), Vector((2.12, -0.8, 2.3))]
    W.emit(deco, 'Glow', gv, _quad2(gv), M, W.hexc('#28343e'), 0.0)
    for sy in (-0.75, 0.75):
        hv = [Vector((2.12, sy - 0.2, 0.85)), Vector((2.12, sy + 0.2, 0.85)), Vector((2.12, sy + 0.2, 1.0)), Vector((2.12, sy - 0.2, 1.0))]
        W.emit(deco, 'Glow', hv, _quad2(hv), M, W.C['gcyan'], 0.0)
    for sx in (-1.4, 1.3):
        for sy in (-1.15, 1.15):
            v, f = W.prim_cyl(10, 0.55, 0.55, 0.45, True, True)
            solid(W, obj, [p - Vector((0, 0, 0.22)) for p in v], f,
                  M @ Matrix.Translation((sx, sy, 0.55)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), grey)
    for i in range(3):   # cargo of hay cubes
        for j in range(2):
            for layer in range(2 if i < 2 else 1):
                v, f = W.prim_box(0.9, 0.85, 0.6)
                W.emit(deco, 'Ruin', v, f, M @ Matrix.Translation((-1.5 + i * 0.95, -0.45 + j * 0.9, 1.05 + layer * 0.6)),
                       lambda fi, cen, nn: W.hexc('#e0b850') if fi % 3 else W.hexc('#c89a3c'), 0.06)
    W.EXCL.append((x, y, 3.0))


def quad_drone(W, name, x, y, face, travel=12, h=4.0):
    nm = f'Mover_{travel}_{name}'
    z = W.ground(x, y) + h
    I = Matrix.Identity(4)
    v, f = W.prim_box(0.9, 0.6, 0.35, 0.8)
    W.emit(nm, 'Ruin', v, f, I, lambda fi, cen, nn: W.hexc('#e8e6e0') if nn.z > -0.3 else W.hexc('#6a6c74'), 0.03)
    gv = [Vector((0.46, -0.2, 0.08)), Vector((0.46, 0.2, 0.08)), Vector((0.46, 0.2, 0.2)), Vector((0.46, -0.2, 0.2))]
    W.emit(nm, 'Glow', gv, _quad2(gv), I, W.C['gcyan'], 0.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tip = Vector((sx * 0.75, sy * 0.6, 0.15))
            v, f = W.prim_tube([(Vector((sx * 0.3, sy * 0.2, 0.15)), 0.05), (tip, 0.05)], 4, True, True)
            W.emit(nm, 'Ruin', v, f, I, W.hexc('#6a6c74'), 0.03)
            v, f = W.prim_cyl(10, 0.32, 0.32, 0.03, True, True)
            W.emit(nm, 'Glow', v, f, Matrix.Translation(tip + Vector((0, 0, 0.05))), W.hexc('#9ae8f0'), 0.0)
    part(W, nm, (x, y, z), face)


def weather_tower(W, x, y, h=7.0):
    obj = bobj(W, x, y)
    z = W.ground(x, y) - 0.1
    M = W.mat_at(x, y, z, W.R.uniform(0, 3))
    v, f = W.prim_box(1.6, 1.6, 1.4, 0.8)
    solid(W, obj, v, f, M, W.hexc('#e07a3a'))
    v, f = W.prim_cyl(8, 0.55, 0.45, h, True)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#e8e6e0') if (int(cen.z) % 3) else W.hexc('#6a6c74'))
    gv = [Vector((-0.3, -0.52, h * 0.62)), Vector((0.3, -0.52, h * 0.62)), Vector((0.3, -0.52, h * 0.78)), Vector((-0.3, -0.52, h * 0.78))]
    W.emit(f'Deco_{W.chunk_of(x, y)}', 'Glow', gv, _quad2(gv), M, W.C['gcyan'], 0.0)
    path = [(Vector((0, 0, h)), 0.4), (Vector((0, 0, h + 0.25)), 1.4), (Vector((0, 0, h + 0.55)), 1.2), (Vector((0, 0, h + 0.75)), 0)]
    v, f = W.prim_tube(path, 10, False, True)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#e8e6e0') if nn.z > 0 else W.hexc('#7a7c84'))
    W.EXCL.append((x, y, 1.6))


def windmill(W, name, x, y, h=11.0, speed='060'):
    """Horizontal-axis windmill: tapered tower, nacelle, four-panel rotor (spinning child)."""
    obj = bobj(W, x, y)
    z = W.ground(x, y) - 0.2
    face = math.radians(-30) + math.pi
    M = W.mat_at(x, y, z, face)
    path = [(Vector((0, 0, 0)), 1.1), (Vector((0, 0, 1.2)), 0.8), (Vector((0, 0, h)), 0.45)]
    v, f = W.prim_tube(path, 8, True)
    solid(W, obj, v, f, M, lambda fi, cen, nn: W.hexc('#ece2cc') if (int(cen.z / 1.5) % 3) else W.hexc('#b8aa90'))
    v, f = W.prim_box(1.0, 2.2, 1.0, 0.85)
    solid(W, obj, v, f, M @ Matrix.Translation((0, 0.2, h - 0.2)), W.hexc('#e07a3a'))
    rot = f'Spin_z_{speed}_{name}'
    for k in range(4):
        a = k * math.pi / 2
        d = Vector((math.cos(a), 0, math.sin(a)))
        side = Vector((-math.sin(a), 0, math.cos(a)))
        bv = [d * 0.5 - side * 0.12, d * 4.6 - side * 0.12, d * 4.6 + side * 0.55, d * 1.0 + side * 0.4]
        W.emit(rot, 'Ruin', bv, _quad2(bv), Matrix.Identity(4),
               lambda fi, cen, nn: W.hexc('#ece2cc'), 0.03)
        v, f = W.prim_tube([(Vector((0, 0, 0)), 0.08), (d * 4.6, 0.06)], 4, True, True)
        W.emit(rot, 'Ruin', v, f, Matrix.Identity(4), W.hexc('#2f6f7a'), 0.03)
    v, f = W.prim_ico(0)
    W.emit(rot, 'Ruin', [p * 0.4 for p in v], f, Matrix.Identity(4), W.hexc('#6a6c74'), 0.03)
    off = Vector((0, -1.0, h - 0.0))
    wp = M @ off
    part(W, rot, (wp.x, wp.y, wp.z), face)
    W.EXCL.append((x, y, 2.0))


def wheat_canopy(W, fi):
    """A swaying golden 'mass' at head height (few triangles) that makes the field read dense and plush;
    individual stalks poke through it. Skirts drop to the ground at every edge (field borders, cut line)."""
    fx, fy, w, l, ang, crop, variety = FIELDS[fi]
    cols = [W.hexc(c) for c in CANOPY[variety]]
    cell = 0.9
    rx = w if crop == 'wheat_round' else w / 2
    ry = w if crop == 'wheat_round' else l / 2
    nx, ny = int(2 * rx / cell) + 1, int(2 * ry / cell) + 1
    c_, s_ = math.cos(ang), math.sin(ang)

    def inside(lx, ly):
        if crop == 'wheat_round':
            rr = math.hypot(lx, ly)
            return rr < w - 0.4 and abs(rr - w * 0.5) > 0.8 and abs(rr - (w - 0.9)) > 0.6 and rr > 1.8
        if abs(lx) > w / 2 - 0.35 or abs(ly) > l / 2 - 0.35:
            return False
        if fi == 3 and ly < -l / 2 + l * HARVESTED + 0.2:
            return False
        return True
    verts = {}
    obj_faces = {}
    R = W.R

    def vid(i, j):
        if (i, j) not in verts:
            lx, ly = -rx + i * cell, -ry + j * cell
            x, y = fx + lx * c_ - ly * s_, fy + lx * s_ + ly * c_
            g = W.ground(x, y)
            bump = 0.12 * math.sin(lx * 1.3 + ly * 0.7) + 0.08 * math.sin(lx * 0.5 - ly * 1.9)
            verts[(i, j)] = (Vector((x, y, g + 0.5 + bump + R.uniform(-0.1, 0.1))), g)
        return (i, j)
    for i in range(nx - 1):
        for j in range(ny - 1):
            lx, ly = -rx + (i + 0.5) * cell, -ry + (j + 0.5) * cell
            if all(inside(-rx + (i + a) * cell, -ry + (j + b) * cell) for a in (0, 1) for b in (0, 1)):
                q = (vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1))
                obj_faces[(i, j)] = q
    # emit top faces + skirts on boundary edges
    edge_count = {}
    for q in obj_faces.values():
        for k in range(4):
            e = (q[k], q[(k + 1) % 4])
            key = tuple(sorted(e))
            edge_count[key] = edge_count.get(key, 0) + 1
    for (i, j), q in obj_faces.items():
        x, y = verts[q[0]][0].x, verts[q[0]][0].y
        obj = f'Wheat_{W.chunk_of(x, y)}'
        a = W.acc(obj)
        b = len(a.v)
        tops = [verts[k][0] for k in q]
        a.v.extend(tops)
        a.uv.extend((0.85, R.random()) for _ in tops)
        for tri in ((0, 1, 2), (0, 2, 3)):
            a.f.append(tuple(b + t for t in tri))
            a.fc.append(W.jit(cols[R.randint(0, 2)], 0.05))
            a.fm.append('Wheat')
        for k in range(4):
            e = (q[k], q[(k + 1) % 4])
            if edge_count[tuple(sorted(e))] == 1:
                p0, g0 = verts[e[0]]
                p1, g1 = verts[e[1]]
                b = len(a.v)
                a.v.extend([p0, p1, Vector((p1.x, p1.y, g1 - 0.05)), Vector((p0.x, p0.y, g0 - 0.05))])
                a.uv.extend([(0.85, 0.0), (0.85, 0.0), (0.0, 0.0), (0.0, 0.0)])
                for tri in ((0, 2, 1), (0, 3, 2)):
                    a.f.append(tuple(b + t for t in tri))
                    a.fc.append(W.jit(W.shade(cols[2], 0.9), 0.05))
                    a.fm.append('Wheat')
    return len(obj_faces) * 2


def clouds(W):
    """Big stylised low-poly cumulus clouds ringing the sky (unshaded, no fog)."""
    R = W.R
    for k in range(14):
        a = k * 2 * math.pi / 14 + R.uniform(-0.15, 0.15)
        d = R.uniform(185, 240)
        cx, cy, cz = math.cos(a) * d, math.sin(a) * d + 40, R.uniform(70, 110)
        obj = f'Cloud_{k}'
        for j in range(R.randint(5, 9)):
            v, f = W.prim_ico(1)
            r_ = R.uniform(9, 18)
            off = Vector((R.uniform(-25, 25), R.uniform(-8, 8), R.uniform(-2, 8)))
            sq = Vector((1.0, 0.8, 0.62))
            W.emit(obj, 'Cloud', [Vector((p.x * r_ * sq.x, p.y * r_ * sq.y, p.z * r_ * sq.z)) + off for p in v], f,
                   Matrix.Rotation(a + math.pi / 2, 4, 'Z'),
                   lambda fi_, cen, nn: W.mix(W.hexc('#b8c8e4'), W.hexc('#ffffff'), W.smooth(-0.6, 0.7, nn.z)), 0.02)
        part(W, obj, (cx, cy, cz))


def far_city(W):
    """A distant city of spires on the northern plateau, seen above the valley rim."""
    R = W.R
    obj = 'Far_city'
    cx, cy = 70.0, 168.0
    for k in range(16):
        x, y = cx + R.uniform(-30, 30), cy + R.uniform(-6, 6)
        g = W.ground(x, y)
        h = R.uniform(18, 60) * (1.4 if k < 3 else 1.0)
        r_ = R.uniform(2.0, 4.5)
        path = [(Vector((x, y, g - 2)), r_ * 1.3), (Vector((x, y, g + h * 0.5)), r_), (Vector((x, y, g + h * 0.85)), r_ * 0.55),
                (Vector((x, y, g + h)), 0)]
        v, f = W.prim_tube(path, 6, False)
        W.emit(obj, 'Ruin', v, f, Matrix.Identity(4),
               lambda fi_, cen, nn: W.hexc('#e8dcc4') if (fi_ // 6) % 3 else W.hexc('#c8643c'), 0.03)
        if k < 6:
            v, f = W.prim_ico(0)
            W.emit(obj, 'Glow', [p * 1.2 + Vector((x, y, g + h * 0.88)) for p in v], f, Matrix.Identity(4), W.C['gcyan'], 0.0)
    for k in range(6):   # domed halls at their feet
        x, y = cx + R.uniform(-28, 28), cy + R.uniform(-8, 4)
        g = W.ground(x, y)
        v, f = W.prim_ico(1)
        rr = R.uniform(6, 11)
        W.emit(obj, 'Ruin', [Vector((p.x * rr, p.y * rr, p.z * rr * 0.6)) + Vector((x, y, g)) for p in v], f, Matrix.Identity(4),
               lambda fi_, cen, nn: W.hexc('#e8dcc4') if nn.z < 0.5 else W.hexc('#c8643c'), 0.03)


# ------------------------------------------------------------------------------------------------ build
def build(W):
    counts = {'wheat_tris': 0, 'row_plants': 0, 'canopy_tris': 0}
    for i, f in enumerate(FIELDS):
        if f[5].startswith('wheat'):
            counts['wheat_tris'] += wheat_field(W, i)
            counts['canopy_tris'] += wheat_canopy(W, i)
        else:
            counts['row_plants'] += row_crops(W, i)
    # field fences (with gates facing the roads), lavender along them
    for i, f in enumerate(FIELDS):
        if f[5] == 'wheat_round':
            continue
        fx, fy, w, l, a = f[:5]
        c, s = math.cos(a), math.sin(a)
        corners = []
        for lx, ly in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            px, py = lx * (w / 2 + 0.8), ly * (l / 2 + 0.8)
            corners.append((fx + px * c - py * s, fy + px * s + py * c))
        for k in [0, 1, 2, 3]:
            a_, b_ = corners[k], corners[(k + 1) % 4]
            mid = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
            fence(W, a_, b_, gap=mid if k == 0 else None)
            for t in (0.2, 0.45, 0.8):
                if W.R.random() < 0.6:
                    px, py = a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t
                    ox, oy = (px - fx) * 0.06, (py - fy) * 0.06
                    lavender(W, px + ox, py + oy)
    # homestead A (west): the main farm hall with tower and silos, barn, windmill, yard clutter
    farm_hall(W, -27.0, 110.0, math.radians(4))
    barn(W, -14.0, 115.0, math.radians(-15))
    silo(W, -36.0, 116.0)
    silo(W, -39.5, 112.0, 7.0, 1.4)
    windmill(W, 'millA', -38.0, 101.0)
    well(W, -21.0, 102.0)
    crawler_tractor(W, -15.0, 104.0, math.radians(160))
    hay_cubes(W, -10.5, 107.5, 6, 0.3)
    crates(W, -22.0, 99.5, 3)
    cart(W, -30.0, 100.5, math.radians(30))
    weather_tower(W, -44.0, 106.0)
    # homestead B (east): round farmhouse, greenhouse, water tower, pods, windmill
    farmhouse(W, 16.0, 117.0, math.radians(-12), 3.6)
    greenhouse(W, 25.0, 109.5)
    water_tower(W, 25.5, 118.5)
    storage_pods(W, 9.5, 108.0)
    windmill(W, 'millB', 6.0, 120.0, 10.0, '075')
    hay_cubes(W, 12.0, 122.5, 5, -0.2)
    crates(W, 21.0, 105.0, 2)
    condenser_spire(W, 30.0, 126.0, 10.0)
    farmhouse(W, 50.0, 110.0, math.radians(140), 3.0)
    weather_tower(W, 48.0, 90.0, 6.0)
    # machinery at work
    f3 = FIELDS[3]
    walker_harvester(W, f3[0] + 7.0, f3[1] - f3[3] / 2 + f3[3] * HARVESTED - 4.0, math.pi / 2)
    hauler(W, -4.0, 97.0, math.radians(90))
    hay_cubes(W, 0.5, 108.0, 6, 0.1)
    pivot_irrigator(W, 5)
    f4 = FIELDS[4]
    quad_drone(W, 'droneA', f4[0], f4[1] - 2.0, f4[4], 12, 3.5)
    quad_drone(W, 'droneB', -42.0, 92.0, 0.1, 16, 5.0)
    f2 = FIELDS[2]
    quad_drone(W, 'droneC', f2[0], f2[1], f2[4], 12, 3.0)
    quad_drone(W, 'droneD', 30.0, 112.0, 0.8, 20, 9.0)
    # shade trees and shrubs on the valley margins, lavender by the roads
    for (tx, ty, ts) in [(-56, 100, 1.1), (-52, 122, 1.0), (-30, 128, 1.2), (4, 132, 1.0), (52, 100, 1.1),
                         (44, 130, 0.9), (-20, 76, 1.0), (22, 80, 1.1), (-34, 82, 0.9), (60, 108, 1.0)]:
        acacia(W, tx, ty, ts)
    for k in range(40):
        a = W.R.uniform(0, 6.283)
        rr = W.R.uniform(0.75, 1.0)
        bx = VALLEY[0] + math.cos(a) * VALLEY[2] * rr
        by = VALLEY[1] + math.sin(a) * VALLEY[3] * rr
        if in_field(bx, by, 2.0) is None and road_d(bx, by) > 3.0 and not W.excluded(bx, by):
            (bush if k % 3 else lavender)(W, bx, by) if k % 3 != 1 else bush(W, bx, by, 0.8)
    for (a, b) in ROADS:
        for t in (0.15, 0.4, 0.65, 0.9):
            px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            side = W.R.choice([-1, 1]) * 3.0
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            qx, qy = px - dy / L * side, py + dx / L * side
            if in_field(qx, qy, 1.0) is None and not W.excluded(qx, qy):
                lavender(W, qx, qy)
    clouds(W)
    far_city(W)
    for x, y, r in YARDS:
        W.EXCL.append((x, y, r * 0.7))
    return counts
