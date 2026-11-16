"""Six humanoid species for the alien planet: procedural low-poly characters on one shared skeleton.

Run either:
    python3 alien_planet/blender/build_characters.py          (pip `bpy` module)
    blender -b -P alien_planet/blender/build_characters.py

Writes
    alien_planet/blender/characters.blend               the whole cast lined up by species (edit in Blender)
    alien_planet/godot/assets/chars/<id>.glb            one rigged, animated character per file
    alien_planet/godot/assets/chars/manifest.json       id, species, name, height, held props

Shared animation framework
- Every character uses the same skeleton: bone names, hierarchy and bone-axis conventions are identical,
  only the bone lengths follow each individual's proportions. Optional extra bones (tail.*, ear.*, antenna.*)
  only exist on species that have them.
- Bone axes: Y runs along the bone, X = Y x world-Y (so +X rotation always swings a bone backwards,
  -X forwards), Z completes the frame (side swing; mirror the sign per side).
- Every character ships the same animation set, generated from the same pose functions but fitted to its
  proportions (stride, sitting height): Idle, Walk, Run, Sit, Talk, Attack.
- Held props (staff, spear, hammer, lantern...) are separate meshes parented to hand.R / hand.L; Godot
  imports them as BoneAttachment3D, so items can be swapped per character.
- Style: flat-shaded low poly, colour in per-face vertex colours, two materials (CharBody, CharGlow).
  Each character is ~1.5-3.5k triangles.
"""
import bpy, json, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, 'godot', 'assets', 'chars')
OUT_BLEND = os.path.join(HERE, 'characters.blend')
FPS = 24
YW = Vector((0, 1, 0))


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def hexc(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def shade(c, k):
    return tuple(clamp(v * k) for v in c)


# ================================================================================================ palettes
P = {k: hexc(v) for k, v in dict(
    ochre='#c8913c', rust='#a4482e', teal='#2f7f7a', indigo='#34407a', cream='#e2d6b8', plum='#6a3a5a',
    moss='#5a6a3a', slate='#4a5060', sand='#c9b08a', crimson='#9a2f3a', leather='#6a4630', dleather='#3e2a20',
    bronze='#a07a40', white='#e8e4dc', lavender='#8a7ab0', black='#1c1a20', silver='#b8bcc8', gold='#d4a84a',
    glowc='#7ae6ee', glowg='#c4f474', glowp='#f07cc6', glowy='#ffd27a', wood='#7a5236', steel='#8a909a',
).items()}

SKIN = {
    'human': ['#f1c9a5', '#e3b08a', '#c88a64', '#a86b4a', '#8a5236', '#6a4029', '#4a2e1f'],
    'avari': ['#a9c1dc', '#b8b6d2', '#c3b5dd', '#9fb2c6', '#cfd8e8', '#aab8d8'],
    'keth': ['#7c7a4e', '#8a6a44', '#6c5c40', '#5e6848', '#9a7a52', '#74583e'],
    'luma': ['#a8d6e0', '#c4b2e2', '#b2dcc2', '#e6c2b4', '#b2c0ec'],
    'vorn': ['#b49a7a', '#9aa08a', '#a88a96', '#c0a68a'],
    'murrai': ['#8a7a9a', '#b08a5a', '#7a5040', '#5e5e6c', '#c8b090', '#6a6050'],
}
HAIR = ['#1e1610', '#3a2414', '#5a3a1e', '#8a5a2a', '#b07a3a', '#d8b878', '#2a2a30', '#7a2a1a']
CLOTH = {
    'human': ['ochre', 'rust', 'teal', 'indigo', 'cream', 'sand', 'moss', 'crimson', 'slate'],
    'avari': ['white', 'lavender', 'indigo', 'teal', 'cream', 'slate'],
    'keth': ['leather', 'dleather', 'bronze', 'rust', 'moss', 'sand'],
    'luma': ['indigo', 'plum', 'teal', 'slate', 'lavender'],
    'vorn': ['ochre', 'dleather', 'crimson', 'slate', 'sand', 'black'],
    'murrai': ['rust', 'teal', 'cream', 'ochre', 'plum', 'moss'],
}


# ================================================================================================ species
# Proportions are fractions of the individual's height H. head = head height, leg = hip height,
# sw = half distance between shoulder joints, hw = half distance between hip joints, limb = limb thickness.
SPECIES = {
    'human': dict(H=(1.58, 1.9), head=0.13, leg=0.5, neck=0.045, sw=0.105, hw=0.055, arm=0.43, limb=1.0,
                  torso=[(-0.06, 0.085, 0.06, 0.0), (0.1, 0.098, 0.066, 0.0), (0.38, 0.084, 0.058, 0.0),
                         (0.66, 0.1, 0.066, -0.004), (0.88, 0.108, 0.06, 0.0), (1.0, 0.045, 0.04, 0.0)]),
    'avari': dict(H=(1.95, 2.24), head=0.125, leg=0.54, neck=0.075, sw=0.088, hw=0.048, arm=0.45, limb=0.76,
                  torso=[(-0.05, 0.072, 0.05, 0.0), (0.1, 0.08, 0.054, 0.0), (0.4, 0.066, 0.048, 0.0),
                         (0.68, 0.082, 0.056, -0.004), (0.9, 0.09, 0.05, 0.0), (1.0, 0.036, 0.032, 0.0)]),
    'keth': dict(H=(1.74, 2.02), head=0.122, leg=0.46, neck=0.035, sw=0.13, hw=0.066, arm=0.44, limb=1.38,
                 torso=[(-0.06, 0.1, 0.07, 0.0), (0.1, 0.112, 0.08, 0.0), (0.38, 0.11, 0.084, -0.008),
                        (0.66, 0.135, 0.085, -0.008), (0.88, 0.14, 0.074, 0.0), (1.0, 0.065, 0.055, 0.0)]),
    'luma': dict(H=(1.74, 1.98), head=0.122, leg=0.53, neck=0.065, sw=0.088, hw=0.05, arm=0.45, limb=0.8,
                 torso=[(-0.05, 0.074, 0.052, 0.0), (0.1, 0.084, 0.056, 0.0), (0.4, 0.068, 0.05, 0.0),
                        (0.68, 0.082, 0.056, 0.0), (0.9, 0.09, 0.052, 0.0), (1.0, 0.036, 0.032, 0.0)]),
    'vorn': dict(H=(1.62, 1.86), head=0.13, leg=0.5, neck=0.05, sw=0.112, hw=0.05, arm=0.48, limb=0.9,
                 torso=[(-0.05, 0.075, 0.058, 0.0), (0.12, 0.082, 0.064, 0.01), (0.36, 0.05, 0.046, 0.0),
                        (0.62, 0.1, 0.072, -0.01), (0.86, 0.118, 0.07, 0.0), (1.0, 0.05, 0.045, 0.0)]),
    'murrai': dict(H=(1.45, 1.76), head=0.15, leg=0.47, neck=0.04, sw=0.1, hw=0.058, arm=0.42, limb=1.05,
                   torso=[(-0.06, 0.088, 0.064, 0.0), (0.1, 0.098, 0.07, 0.0), (0.4, 0.088, 0.066, 0.0),
                          (0.66, 0.1, 0.07, -0.006), (0.88, 0.104, 0.064, 0.0), (1.0, 0.05, 0.045, 0.0)]),
}

# Head loft rings (t from chin 0 to crown 1): (t, half-width, half-depth, y offset), in units of head height.
HEADS = {
    'human': [(0.0, 0.16, 0.16, -0.24), (0.12, 0.42, 0.4, -0.1), (0.32, 0.56, 0.54, -0.02), (0.55, 0.6, 0.6, 0.02),
              (0.78, 0.58, 0.62, 0.05), (0.94, 0.42, 0.48, 0.07), (1.0, 0.12, 0.14, 0.07)],
    'avari': [(0.0, 0.12, 0.12, -0.2), (0.14, 0.3, 0.32, -0.1), (0.34, 0.44, 0.46, -0.02), (0.52, 0.52, 0.56, 0.04),
              (0.72, 0.56, 0.7, 0.14), (0.88, 0.5, 0.72, 0.2), (0.98, 0.32, 0.5, 0.22), (1.06, 0.1, 0.14, 0.2)],
    'keth': [(0.0, 0.34, 0.24, -0.22), (0.14, 0.6, 0.46, -0.12), (0.34, 0.66, 0.58, -0.04), (0.56, 0.62, 0.6, 0.0),
             (0.76, 0.56, 0.6, 0.05), (0.92, 0.42, 0.5, 0.08), (1.0, 0.16, 0.2, 0.08)],
    'luma': [(0.0, 0.12, 0.12, -0.2), (0.14, 0.34, 0.34, -0.1), (0.36, 0.48, 0.5, -0.02), (0.58, 0.54, 0.58, 0.03),
             (0.8, 0.52, 0.62, 0.08), (0.96, 0.36, 0.5, 0.12), (1.06, 0.1, 0.14, 0.12)],
    'vorn': [(0.0, 0.14, 0.14, -0.2), (0.14, 0.36, 0.36, -0.1), (0.34, 0.5, 0.5, -0.03), (0.56, 0.64, 0.58, 0.0),
             (0.76, 0.7, 0.6, 0.04), (0.92, 0.58, 0.52, 0.06), (1.0, 0.2, 0.2, 0.06)],
    'murrai': [(0.0, 0.2, 0.18, -0.22), (0.14, 0.5, 0.44, -0.08), (0.34, 0.66, 0.56, -0.01), (0.56, 0.64, 0.58, 0.02),
               (0.78, 0.6, 0.6, 0.04), (0.94, 0.44, 0.48, 0.06), (1.0, 0.14, 0.14, 0.06)],
}

NAMES = {
    'human': ['Ilsa', 'Dorran', 'Mbeki', 'Senna', 'Old Haro', 'Pip'],
    'avari': ['Ithelle', 'Saevor', 'Myriel', 'Orrandin', 'Elder Vaesh'],
    'keth': ['Gruda', 'Tarrok', 'Hessa', 'Borro', 'Old Kaldrun'],
    'luma': ['Seylin', 'Aoren', 'Fennia', 'Liriel', 'Thaom'],
    'vorn': ['Zik-Ara', 'Tchoss', 'Mivvet', 'Krell-Oan', 'Ossik'],
    'murrai': ['Tamsu', 'Rhuun', 'Kiri', 'Orbek', 'Old Mahrra'],
}

SPECIES_INFO = {
    'human': 'Humans: long-settled people of the planet, farmers, traders and wanderers.',
    'avari': 'Avari: tall, slender keepers of the old ring-shrines and their glyph lore.',
    'keth': 'Keth: broad, scaled builders and smiths; patient, proud and plain-spoken.',
    'luma': 'Luma: slim, softly glowing folk whose skin patterns brighten in the dark.',
    'vorn': 'Vorn: plated, many-eyed tinkerers who taste the air with their feelers.',
    'murrai': 'Murrai: furred, long-eared, tailed nomads of the grass basins.',
}


# ================================================================================================ mesh accumulator
class CMesh:
    def __init__(self):
        self.v, self.f, self.fc, self.fm, self.w = [], [], [], [], []

    def add(self, verts, faces, color, weights, mat='CharBody', jitter=0.03, rng=None):
        """weights: bone name, list per vertex of [(bone, w)], or fn(i, pos) -> [(bone, w)]."""
        rng = rng or random
        base = len(self.v)
        self.v.extend(verts)
        for i, p in enumerate(verts):
            if isinstance(weights, str):
                self.w.append([(weights, 1.0)])
            elif callable(weights):
                self.w.append(weights(i, p))
            else:
                self.w.append(weights[i])
        for fi, f in enumerate(faces):
            self.f.append(tuple(base + k for k in f))
            if callable(color):
                ps = [verts[k] for k in f]
                cen = sum(ps, Vector()) / len(ps)
                n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
                n = n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))
                c = color(fi, cen, n)
            else:
                c = color
            k = 1.0 + rng.uniform(-jitter, jitter)
            self.fc.append(shade(c, k))
            self.fm.append(mat)


def bone_axes(d):
    d = d.normalized()
    x = d.cross(YW)
    if x.length < 1e-4:
        x = Vector((1, 0, 0))
    x.normalize()
    z = x.cross(d).normalized()
    return x, z


def ring(center, d, rx, rz, n, phase=0.0, squash=None):
    """Ring of n points around `center`, perpendicular to direction d, using the bone-axis convention."""
    x, z = bone_axes(d)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n + phase
        pts.append(center + x * math.cos(a) * rx + z * math.sin(a) * rz)
    return pts


def loft(rings, cap_start=False, cap_end=False):
    """Faces joining consecutive rings (same vertex count); returns verts, faces."""
    verts, faces = [], []
    n = len(rings[0])
    for r in rings:
        verts.extend(r)
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for k in range(n):
            faces.append((a + k, a + (k + 1) % n, b + (k + 1) % n, b + k))
    if cap_start:
        faces.append(tuple(reversed(range(n))))
    if cap_end:
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return verts, faces


def disc(center, normal, up, rw, rh, n=8, bulge=0.0):
    """A flat (slightly bulged) n-gon facing `normal`, for eyes, markings and plates."""
    normal = normal.normalized()
    right = up.cross(normal).normalized()
    up2 = normal.cross(right).normalized()
    v = [center + normal * bulge]
    for k in range(n):
        a = 2 * math.pi * k / n
        v.append(center + right * math.cos(a) * rw + up2 * math.sin(a) * rh)
    f = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    return v, f


def box(c, sx, sy, sz, M=None):
    x, y, z = sx / 2, sy / 2, sz / 2
    v = [Vector(p) for p in [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
                             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]]
    if M is not None:
        v = [M @ p for p in v]
    v = [c + p for p in v]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


def ico(c, r, sx=1.0, sy=1.0, sz=1.0, sub=0):
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
        for a, b, cc in f:
            ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a)
            nf += [(a, ab, ca), (b, bc, ab), (cc, ca, bc), (ab, bc, ca)]
        f = nf
    return [c + Vector((p.x * r * sx, p.y * r * sy, p.z * r * sz)) for p in v], f


def cone(base, tip, r, n=5):
    d = tip - base
    pts = ring(base, d, r, r, n)
    v = pts + [tip]
    f = [(k, (k + 1) % n, n) for k in range(n)] + [tuple(reversed(range(n)))]
    return v, f


# ================================================================================================ individual
class Char:
    """One individual: proportions -> joints -> skeleton, plus design choices."""

    def __init__(self, species, idx, seed):
        self.sp = species
        self.S = SPECIES[species]
        self.idx = idx
        self.r = random.Random(seed)
        r = self.r
        self.name = NAMES[species][idx % len(NAMES[species])]
        self.id = f'{species}_{idx}'
        # age & build
        self.age = 'adult'
        if self.name.startswith(('Old ', 'Elder ')) or (species == 'luma' and idx == 4) or (species == 'vorn' and idx == 4):
            self.age = 'elder'
        if self.name == 'Pip' or (species == 'murrai' and idx == 2):
            self.age = 'young'
        self.build = r.choice(['slim', 'average', 'average', 'heavy']) if self.age != 'young' else 'slim'
        if species == 'keth' and self.build == 'slim':
            self.build = 'average'
        self.fem = r.random() < 0.5
        lo, hi = self.S['H']
        H = r.uniform(lo, hi)
        if self.fem:
            H *= 0.96
        if self.age == 'young':
            H *= 0.66
        if self.age == 'elder':
            H *= 0.97
        self.H = H
        self.bulk = {'slim': 0.86, 'average': 1.0, 'heavy': 1.2}[self.build] * self.S['limb']
        self.skin = hexc(r.choice(SKIN[species]))
        self.hunch = 0.12 if self.age == 'elder' else 0.0
        self.colors = [P[c] for c in r.sample(CLOTH[species], 3)]
        self.extra_bones = []
        self.props = []
        self.joints()

    # ------------------------------------------------------------------ skeleton (rest A-pose)
    def joints(self):
        S, H = self.S, self.H
        head_k = S['head'] * (1.3 if self.age == 'young' else 1.0)
        hh = H * head_k
        self.hh = hh
        neck = H * S['neck']
        hip_z = H * S['leg'] * (0.93 if self.age == 'young' else 1.0)
        top = H
        head_base = top - hh
        neck_base = head_base - neck
        sh_z = neck_base - H * 0.02
        self.hip_z, self.neck_base, self.head_base = hip_z, neck_base, head_base
        sw = H * S['sw'] * (1.06 if not self.fem else 0.95) * (1.08 if self.build == 'heavy' else 1.0)
        hw = H * S['hw'] * (1.08 if self.fem else 1.0)
        arm = H * S['arm']
        ua, fa, hand = arm * 0.44, arm * 0.4, arm * 0.16
        a = math.radians(48)   # A-pose: arms 48 degrees below horizontal
        J = {}
        J['hips'] = (Vector((0, 0, hip_z)), Vector((0, 0, hip_z + 0.08 * H)))
        spine_top = hip_z + (neck_base - hip_z) * 0.45
        J['spine'] = (Vector((0, 0, hip_z + 0.08 * H)), Vector((0, 0, spine_top)))
        J['chest'] = (Vector((0, 0, spine_top)), Vector((0, 0, neck_base)))
        J['neck'] = (Vector((0, -0.01 * H, neck_base)), Vector((0, -0.012 * H, head_base)))
        J['head'] = (Vector((0, -0.012 * H, head_base)), Vector((0, -0.012 * H, top)))
        for s, sg in (('L', 1), ('R', -1)):
            sh = Vector((sg * sw, 0.004 * H, sh_z))
            J[f'shoulder.{s}'] = (Vector((sg * 0.02 * H, 0, sh_z + 0.01 * H)), sh)
            dirv = Vector((sg * math.cos(a), 0.0, -math.sin(a)))
            el = sh + dirv * ua
            wr = el + dirv * fa
            J[f'upper_arm.{s}'] = (sh, el)
            J[f'forearm.{s}'] = (el, wr)
            J[f'hand.{s}'] = (wr, wr + dirv * hand)
            hp = Vector((sg * hw, 0, hip_z))
            ankle_z = H * 0.045
            kn = Vector((sg * hw * 1.02, -0.008 * H, ankle_z + (hip_z - ankle_z) * 0.5))
            an = Vector((sg * hw * 1.04, 0.0, ankle_z))
            J[f'thigh.{s}'] = (hp, kn)
            J[f'shin.{s}'] = (kn, an)
            J[f'foot.{s}'] = (an, Vector((sg * hw * 1.06, -H * 0.085, 0.018 * H)))
        self.J = J
        self.parents = {'spine': 'hips', 'chest': 'spine', 'neck': 'chest', 'head': 'neck'}
        for s in 'LR':
            self.parents.update({f'shoulder.{s}': 'chest', f'upper_arm.{s}': f'shoulder.{s}',
                                 f'forearm.{s}': f'upper_arm.{s}', f'hand.{s}': f'forearm.{s}',
                                 f'thigh.{s}': 'hips', f'shin.{s}': f'thigh.{s}', f'foot.{s}': f'shin.{s}'})
        self.ua, self.fa, self.hand = ua, fa, hand
        self.thigh_len = (J['thigh.L'][0] - J['thigh.L'][1]).length

    def add_bone(self, name, head, tail, parent):
        self.J[name] = (head, tail)
        self.parents[name] = parent
        self.extra_bones.append(name)

    def bdir(self, b):
        h, t = self.J[b]
        return (t - h)

    # ------------------------------------------------------------------ body
    def torso_rings(self, n=8, scale=1.0, t0=-1.0, t1=2.0):
        """Rings along the torso from crotch to neck base: (center, rx, ry, t)."""
        H = self.H
        out = []
        for (t, w, d, yo) in self.S['torso']:
            if t < t0 or t > t1:
                continue
            z = lerp(self.hip_z, self.neck_base, t)
            wk = w * H
            dk = d * H
            if t <= 0.15:   # hips
                wk *= (1.1 if self.fem else 1.0) * (1.1 if self.build == 'heavy' else 1.0)
            elif t < 0.5:   # waist / belly
                wk *= {'slim': 0.92, 'average': 1.0, 'heavy': 1.22}[self.build]
                dk *= {'slim': 0.92, 'average': 1.0, 'heavy': 1.35}[self.build]
            elif t < 0.95:   # chest / shoulders
                wk *= (0.95 if self.fem else 1.04) * (1.1 if self.build == 'heavy' else 1.0)
                dk *= (1.08 if self.fem and t < 0.75 else 1.0) * (1.1 if self.build == 'heavy' else 1.0)
            y = yo * H + self.hunch * (t ** 2) * 0.12 * H
            out.append((Vector((0, y, z)), wk * scale, dk * scale, t))
        return out

    def torso_at(self, t, scale=1.0):
        """Interpolated torso ring at t: (center, rx, ry)."""
        tr = self.torso_rings(8, scale)
        if t <= tr[0][3]:
            return tr[0][:3]
        for a, b in zip(tr, tr[1:]):
            if a[3] <= t <= b[3]:
                u = (t - a[3]) / max(1e-6, b[3] - a[3])
                return a[0].lerp(b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)
        return tr[-1][:3]

    def torso_weight(self, t):
        if t <= 0.12:
            return [('hips', 1.0)]
        if t <= 0.3:
            return [('hips', 0.5), ('spine', 0.5)]
        if t <= 0.5:
            return [('spine', 1.0)]
        if t <= 0.6:
            return [('spine', 0.4), ('chest', 0.6)]
        if t < 0.99:
            return [('chest', 1.0)]
        return [('chest', 0.5), ('neck', 0.5)]

    def build_torso(self, m, color, scale=1.0, t0=-1.0, t1=2.0, n=8, mat='CharBody', cap=True):
        prof = [r[3] for r in self.torso_rings(n, scale)]
        ts = sorted(set([t for t in prof if t0 < t < t1] + [max(t0, prof[0]), min(t1, prof[-1])]))
        rings_ = [self.torso_at(t, scale) + (t,) for t in ts]
        R = []
        W = []
        for c, rx, ry, t in rings_:
            pts = [c + Vector((math.cos(2 * math.pi * k / n + math.pi / n) * rx,
                               math.sin(2 * math.pi * k / n + math.pi / n) * ry, 0)) for k in range(n)]
            R.append(pts)
            W += [self.torso_weight(t)] * n
        v, f = loft(R, cap_start=cap, cap_end=False)
        m.add(v, f, color, W, mat, rng=self.r)

    def limb_rings(self, bone_a, bone_b, radii, n=6, scale=1.0):
        """Tube through bone_a then bone_b: radii list of (fraction along a+b in 0..2, r, weights)."""
        out = []
        for frac, rr, w in radii:
            b = bone_a if frac <= 1.0 else bone_b
            ff = frac if frac <= 1.0 else frac - 1.0
            h, t = self.J[b]
            p = h + (t - h) * ff
            out.append((p, t - h, rr * scale, w))
        return out

    def tube(self, m, rings_, color, n=6, cap_end=True, cap_start=False, mat='CharBody', flat=1.0):
        R, W = [], []
        for p, d, rr, w in rings_:
            R.append(ring(p, d, rr, rr * flat, n, math.pi / n))
            W += [w] * n
        v, f = loft(R, cap_start, cap_end)
        m.add(v, f, color, W, mat, rng=self.r)

    @staticmethod
    def _span(rs, start, end):
        """Defined rings inside [start, end] plus interpolated rings exactly at start and end."""
        def at(fr):
            for a, b in zip(rs, rs[1:]):
                if a[0] <= fr <= b[0]:
                    u = (fr - a[0]) / max(1e-6, b[0] - a[0])
                    return (fr, lerp(a[1], b[1], u), a[2] if u < 0.5 else b[2])
            return rs[0] if fr <= rs[0][0] else rs[-1]
        inner = [r for r in rs if start + 1e-6 < r[0] < end - 1e-6]
        return [at(start)] + inner + [at(end)]

    def arm_rings(self, s, scale=1.0, start=0.0, end=2.0):
        k = self.bulk * self.H / 1.75
        ua, fa = f'upper_arm.{s}', f'forearm.{s}'
        rs = [(0.0, 0.058 * k, [(ua, 0.7), (f'shoulder.{s}', 0.3)]), (0.5, 0.05 * k, [(ua, 1.0)]),
              (1.0, 0.04 * k, [(ua, 0.5), (fa, 0.5)]), (1.5, 0.042 * k, [(fa, 1.0)]),
              (2.0, 0.03 * k, [(fa, 0.6), (f'hand.{s}', 0.4)])]
        return self.limb_rings(ua, fa, self._span(rs, start, end), scale=scale)

    def leg_rings(self, s, scale=1.0, start=0.0, end=2.0):
        k = self.bulk * self.H / 1.75
        th, sh = f'thigh.{s}', f'shin.{s}'
        rs = [(0.0, 0.085 * k, [('hips', 0.4), (th, 0.6)]), (0.4, 0.078 * k, [(th, 1.0)]),
              (1.0, 0.055 * k, [(th, 0.5), (sh, 0.5)]), (1.35, 0.058 * k, [(sh, 1.0)]),
              (2.0, 0.038 * k, [(sh, 0.6), (f'foot.{s}', 0.4)])]
        return self.limb_rings(th, sh, self._span(rs, start, end), scale=scale)

    def build_hand(self, m, s, color, mitten=True):
        h, t = self.J[f'hand.{s}']
        d = t - h
        k = self.H / 1.75 * (1.2 if self.sp == 'keth' else 1.0)
        x, z = bone_axes(d)
        c = h + d * 0.45
        hw_, ht = 0.042 * k, 0.022 * k
        M = Matrix((x, d.normalized(), z)).transposed()
        v, f = box(Vector((0, 0, 0)), hw_ * 2, d.length * 1.05, ht * 2)
        v = [c + M @ p for p in v]
        m.add(v, f, color, f'hand.{s}', rng=self.r)
        # thumb, pointing forward and in
        tb = h + d * 0.25 - z * 0.01 * k
        tv, tf = cone(tb, tb + d * 0.35 - z * 0.035 * k - x * (0.02 if s == 'L' else -0.02) * k, 0.014 * k, 4)
        m.add(tv, tf, color, f'hand.{s}', rng=self.r)
        if self.sp == 'vorn':   # two hooked fingers instead of a mitten tip
            for o in (-1, 1):
                fb = t + x * o * 0.016 * k
                fv, ff = cone(fb, fb + d * 0.35 + z * 0.01, 0.012 * k, 4)
                m.add(fv, ff, shade(color, 0.7), f'hand.{s}', rng=self.r)

    def build_foot(self, m, s, color, scale=1.0, boot=False):
        a, t = self.J[f'foot.{s}']
        k = self.H / 1.75 * scale * (1.15 if self.sp == 'keth' else 1.0)
        length = (t - a).length + 0.04 * k
        c = Vector((a.x, (a.y + t.y) / 2 - 0.005, 0.03 * k))
        v, f = box(c, 0.085 * k * self.bulk ** 0.3, length, 0.06 * k)
        # taper the toe
        for i in (0, 1, 4, 5):
            v[i] = v[i] + Vector((0, 0, -0.0)) if i < 4 else v[i] + Vector((0, 0, -0.025 * k))
        m.add(v, f, color, [[(f'foot.{s}', 0.8), (f'shin.{s}', 0.2)]] * 8, rng=self.r)
        if self.sp == 'murrai':   # three toe pads at the front
            for o in (-1, 0, 1):
                tv, tf = ico(Vector((c.x + o * 0.025 * k, c.y - length * 0.5, 0.02 * k)), 0.02 * k, 1, 1.2, 0.8)
                m.add(tv, tf, shade(color, 0.85), f'foot.{s}', rng=self.r)


# ================================================================================================ heads & faces
class Head:
    def __init__(self, ch, profile):
        self.ch = ch
        self.prof = profile
        hb = ch.J['head'][0]
        self.base = hb
        self.hh = ch.hh

    def at(self, t):
        pr = self.prof
        for i in range(len(pr) - 1):
            if pr[i][0] <= t <= pr[i + 1][0]:
                u = (t - pr[i][0]) / max(1e-6, pr[i + 1][0] - pr[i][0])
                return tuple(lerp(pr[i][j], pr[i + 1][j], u) for j in range(1, 4))
        return pr[-1][1:] if t > pr[-1][0] else pr[0][1:]

    def surf(self, t, x_frac, out=0.0):
        """Front surface point at height t, across-face x (fraction of half width, -1..1)."""
        w, d, yo = self.at(t)
        hh = self.hh
        x = x_frac * w
        y = yo - d * math.sqrt(max(0.0, 1 - x_frac * x_frac))
        n = Vector((x_frac / max(w, 1e-3), -math.sqrt(max(0.0, 1 - x_frac * x_frac)) / max(d, 1e-3), 0)).normalized()
        p = self.base + Vector((x * hh, y * hh, t * hh)) + n * out * hh
        return p, n

    def build(self, m, color, n=10, sub_rings=None):
        R = []
        W = []
        for (t, w, d, yo) in self.prof:
            c = self.base + Vector((0, yo * self.hh, t * self.hh))
            pts = [c + Vector((math.sin(2 * math.pi * k / n) * w * self.hh, -math.cos(2 * math.pi * k / n) * d * self.hh, 0))
                   for k in range(n)]
            R.append(pts)
            W += [[('head', 1.0)]] * n
        v, f = loft(R, True, True)
        m.add(v, f, color, W, rng=self.ch.r, jitter=0.02)


def eye(m, head, t, xf, size, ch, iris, pupil='#141018', sclera=True, glow=False, slit=False, almond=1.0,
        tilt=0.0, out=0.01):
    p, n = head.surf(t, xf, out)
    up = Vector((math.sin(tilt) * (1 if xf > 0 else -1), 0, math.cos(tilt)))
    hh = head.hh
    lay = 0.004 * hh
    if sclera:
        v, f = disc(p, n, up, size * hh * almond, size * hh * 0.72, 8, 0.003 * hh)
        m.add(v, f, hexc('#f2efe8'), 'head', rng=ch.r, jitter=0.0)
        p = p + n * lay
    ir = size * (0.62 if sclera else 1.0)
    v, f = disc(p, n, up, ir * hh * (1.0 if sclera else almond), ir * hh * (0.95 if sclera else 0.7), 7, 0.002 * hh)
    m.add(v, f, iris, 'head', mat='CharGlow' if glow else 'CharBody', rng=ch.r, jitter=0.0)
    if not glow:
        p2 = p + n * lay
        if slit:
            v, f = disc(p2, n, up, ir * hh * 0.18, ir * hh * 0.8, 6, 0.0)
        else:
            v, f = disc(p2, n, up, ir * hh * 0.45, ir * hh * 0.45, 6, 0.0)
        m.add(v, f, hexc(pupil), 'head', rng=ch.r, jitter=0.0)
        # catch-light
        right = up.cross(n).normalized()
        hp = p2 + n * lay + up * ir * hh * 0.35 + right * ir * hh * 0.25
        v, f = disc(hp, n, up, ir * hh * 0.17, ir * hh * 0.17, 4, 0.0)
        m.add(v, f, hexc('#ffffff'), 'head', rng=ch.r, jitter=0.0)


def brow(m, head, t, xf, length, ch, color, angle=0.0, thick=0.035, out=0.02):
    p, n = head.surf(t, xf, out)
    hh = head.hh
    side = 1 if xf > 0 else -1
    right = Vector((0, 0, 1)).cross(n).normalized()
    a = p - right * length * hh * 0.5
    b = p + right * length * hh * 0.5
    a.z += angle * side * hh * 0.5 * length
    b.z -= angle * side * hh * 0.5 * length
    path = [(a, thick * hh * 0.6), (b, thick * hh * 0.5)]
    R = [ring(pp, b - a, rr, rr * 0.6, 4) for pp, rr in path]
    v, f = loft(R, True, True)
    m.add(v, f, color, 'head', rng=ch.r)


def mouth(m, head, t, width, ch, color='#5a2a2a', out=0.008, smile=0.0, lips=None):
    hh = head.hh
    pts = []
    for xf in (-width, -width * 0.4, 0.0, width * 0.4, width):
        p, n = head.surf(t, xf, out)
        p.z += smile * hh * (abs(xf) / max(width, 1e-3)) ** 2 * 0.06
        pts.append(p)
    v, f = [], []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        base = len(v)
        v += [a + Vector((0, 0, -0.008 * hh)), b + Vector((0, 0, -0.008 * hh)), b + Vector((0, 0, 0.008 * hh)),
              a + Vector((0, 0, 0.008 * hh))]
        f.append((base, base + 1, base + 2, base + 3))
    m.add(v, f, hexc(color), 'head', rng=ch.r, jitter=0.0)
    if lips:
        p, n = head.surf(t - 0.04, 0, out + 0.004)
        lv, lf = disc(p, n, Vector((0, 0, 1)), width * head.at(t)[0] * hh * 0.9, 0.025 * hh, 6, 0.006 * hh)
        m.add(lv, lf, lips, 'head', rng=ch.r)


def nose(m, head, t, ch, color, length=0.12, width=0.1, height=0.16, out=0.0):
    p, n = head.surf(t, 0, out)
    hh = head.hh
    tip = p + Vector((0, -length * hh, -height * hh * 0.35))
    v = [p + Vector((0, 0.0, height * hh * 0.5)), p + Vector((-width * hh, 0.02 * hh, -height * hh * 0.5)),
         p + Vector((width * hh, 0.02 * hh, -height * hh * 0.5)), tip]
    f = [(0, 1, 3), (0, 3, 2), (1, 2, 3)]
    m.add(v, f, shade(color, 1.05), 'head', rng=ch.r)


def hair_cap(m, ch, head, color, front_t=0.8, back_t=0.42, scale=1.06, n=10, fringe=0.0):
    """Hair shell over the skull, cut at the hairline (front) and nape (back)."""
    hh = head.hh
    prof = [p for p in head.prof if p[0] >= back_t - 0.001]
    if prof[0][0] > back_t:
        prof = [(back_t,) + head.at(back_t)] + prof
    R = []
    for (t, w, d, yo) in prof:
        c = head.base + Vector((0, yo * hh, t * hh + 0.01 * hh))
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n
            pts.append(c + Vector((math.sin(a) * w * hh * scale, -math.cos(a) * d * hh * scale, 0)))
        R.append(pts)
    v, f = loft(R, False, True)
    keep = []
    for face in f:
        ps = [v[i] for i in face]
        cen = sum(ps, Vector()) / len(ps)
        tt = (cen.z - head.base.z) / hh
        front = (cen.y - head.base.y) / hh < -0.15
        if front and tt < front_t - fringe and abs(cen.x - head.base.x) / hh < 0.38:
            continue
        keep.append(face)
    m.add(v, keep, color, 'head', rng=ch.r, jitter=0.05)


# ================================================================================================ clothing & gear
def shirt(ch, m, color, sleeves='long', t0=-0.02, t1=0.97, collar=None, scale=1.07):
    ch.build_torso(m, color, scale, t0, t1, cap=False)
    for s in 'LR':
        end = {'none': -1, 'short': 0.55, 'long': 1.9}[sleeves]
        if end > 0:
            rr = ch.arm_rings(s, 1.18, 0.0, end)
            ch.tube(m, rr, color, cap_end=False)
            if sleeves == 'long':   # cuff
                cu = ch.arm_rings(s, 1.32, 1.75, 1.9)
                ch.tube(m, cu, shade(color, 0.75), cap_end=False)
    if collar:
        neck = ch.J['neck'][0]
        c = neck + Vector((0, 0, 0.005 * ch.H))
        rr = 0.05 * ch.H * (1.3 if ch.sp == 'keth' else 1.0)
        R = [ring(c, Vector((0, 0, 1)), rr, rr * 0.85, 8), ring(c + Vector((0, 0.004 * ch.H, 0.035 * ch.H)), Vector((0, 0, 1)), rr * 0.82,
                                                                   rr * 0.72, 8)]
        v, f = loft(R)
        m.add(v, f, collar, [[('chest', 0.6), ('neck', 0.4)]] * 16, rng=ch.r)


def trousers(ch, m, color, end=1.9, scale=1.12):
    for s in 'LR':
        ch.tube(m, ch.leg_rings(s, scale, 0.0, end), color, cap_end=False)
    ch.build_torso(m, color, scale * 0.98, -1, 0.14, cap=True)


def skirt(ch, m, color, length=0.9, flare=1.6, top_t=0.12, n=10, hem=None):
    """Robe / kilt cone from the waist; lower rings blend toward the thighs so walking deforms it."""
    H = ch.H
    c, rx, ry = ch.torso_at(top_t, 1.1)
    z0 = c.z
    z1 = max(0.05 * H, ch.hip_z - length * ch.hip_z)
    R, W = [], []
    steps = 4
    for i in range(steps + 1):
        u = i / steps
        z = lerp(z0, z1, u)
        k = lerp(1.0, flare, u ** 1.2)
        pts = []
        ww = []
        for j in range(n):
            a = 2 * math.pi * j / n + math.pi / n
            x = math.cos(a) * rx * k * 1.05
            y = math.sin(a) * ry * k * 1.15 + c.y
            pts.append(Vector((x, y, z)))
            if u < 0.2:
                ww.append([('hips', 1.0)])
            else:
                side = 'L' if x > 0 else 'R'
                sw_ = clamp(abs(x) / (rx * k)) * min(1.0, u * 1.2)
                ww.append([('hips', 1.0 - 0.6 * sw_), (f'thigh.{side}', 0.6 * sw_)])
        R.append(pts)
        W += ww
    v, f = loft(R)
    m.add(v, f, color, W, rng=ch.r)
    if hem:
        last = R[-1]
        R2 = [last, [p + Vector((0, 0, 0.03 * H)) + (p - Vector((0, c.y, p.z))).normalized() * 0.006 * H for p in last]]
        hv, hf = loft(R2)
        m.add(hv, hf, hem, W[-n:] * 2, mat='CharGlow' if hem in (P['glowc'], P['glowp']) else 'CharBody', rng=ch.r)


def boots(ch, m, color, height=0.45):
    for s in 'LR':
        ch.build_foot(m, s, color, 1.15)
        ch.tube(m, ch.leg_rings(s, 1.2, 2.0 - height, 2.0), color, cap_end=False)


def belt(ch, m, color, t=0.1, buckle=None):
    c, rx, ry = ch.torso_at(t, 1.14)
    z = c.z
    R = [ring(Vector((0, c.y, z - 0.012 * ch.H)), Vector((0, 0, 1)), rx, ry, 8),
         ring(Vector((0, c.y, z + 0.012 * ch.H)), Vector((0, 0, 1)), rx, ry, 8)]
    v, f = loft(R)
    m.add(v, f, color, [ch.torso_weight(t)] * 16, rng=ch.r)
    if buckle:
        bv, bf = box(Vector((0, c.y - ry * 1.02, z)), 0.035 * ch.H, 0.01 * ch.H, 0.03 * ch.H)
        m.add(bv, bf, buckle, 'hips', rng=ch.r)


def sash(ch, m, color, side=1, width=0.035):
    """Diagonal band from one shoulder to the opposite hip, front and back."""
    H = ch.H
    pts = []
    for i in range(9):
        u = i / 8
        t = lerp(0.92, 0.08, u)
        cc, rx, ry = ch.torso_at(t, 1.1)
        cy = cc.y
        x = side * lerp(0.75, -0.75, u)
        z = lerp(ch.hip_z, ch.neck_base, t)
        yf = cy - ry * math.sqrt(max(0.0, 1 - x * x)) * 1.12
        yb = cy + ry * math.sqrt(max(0.0, 1 - x * x)) * 1.12
        pts.append((Vector((x * rx * 1.08, yf, z)), Vector((x * rx * 1.08, yb, z)), ch.torso_weight(t)))
    for idx in (0, 1):
        v, f, W = [], [], []
        for i, pp in enumerate(pts):
            p = pp[idx]
            v += [p + Vector((0, 0, -width * H / 2)), p + Vector((0, 0, width * H / 2))]
            W += [pp[2], pp[2]]
        for i in range(len(pts) - 1):
            a = i * 2
            f.append((a, a + 2, a + 3, a + 1) if idx == 0 else (a, a + 1, a + 3, a + 2))
        m.add(v, f, color, W, rng=ch.r)


def scarf(ch, m, color, tail=True):
    H = ch.H
    c = ch.J['neck'][0] + Vector((0, 0, 0.012 * H))
    rr = 0.052 * H * (1.25 if ch.sp == 'keth' else 1.0)
    R = [ring(c, Vector((0, 0, 1)), rr * 1.15, rr, 8), ring(c + Vector((0, 0, 0.04 * H)), Vector((0, 0, 1)), rr * 0.95, rr * 0.85, 8)]
    v, f = loft(R, True, False)
    m.add(v, f, color, [[('chest', 0.5), ('neck', 0.5)]] * 16, rng=ch.r)
    if tail:
        s = ch.r.choice([-1, 1])
        a = c + Vector((s * rr * 0.5, -rr * 0.9, 0))
        path = [a, a + Vector((s * 0.02 * H, -0.03 * H, -0.12 * H)), a + Vector((s * 0.03 * H, -0.035 * H, -0.24 * H))]
        R = [ring(p, Vector((0, 0, -1)), 0.03 * H, 0.008 * H, 4) for p in path]
        v, f = loft(R, False, True)
        m.add(v, f, shade(color, 0.9), 'chest', rng=ch.r)


def cape(ch, m, color, length=0.75, hood=False, trim=None):
    H = ch.H
    sl, sr = ch.J['upper_arm.L'][0], ch.J['upper_arm.R'][0]
    top = ch.neck_base + 0.005 * H
    rows = 4
    v, f, W = [], [], []
    cols = 5
    for i in range(rows + 1):
        u = i / rows
        z = lerp(top, top - length * (top - 0.08 * H), u)
        spread = lerp(1.0, 1.35, u)
        for j in range(cols):
            x = lerp(sr.x, sl.x, j / (cols - 1)) * spread * 1.15
            back = 0.075 * H * (1.25 if ch.build == 'heavy' or ch.sp == 'keth' else 1.0) + 0.02 * H * u
            y = back + 0.015 * H * math.cos((j / (cols - 1) - 0.5) * math.pi) * (1 - u)
            v.append(Vector((x, y, z)))
            if u < 0.35:
                W.append([('chest', 1.0)])
            else:
                W.append([('spine', 0.6), ('chest', 0.4)] if u < 0.7 else [('hips', 0.5), ('spine', 0.5)])
    for i in range(rows):
        for j in range(cols - 1):
            a = i * cols + j
            f.append((a, a + 1, a + cols + 1, a + cols))
    m.add(v, f, color, W, rng=ch.r)
    if hood:
        hb = ch.J['head'][0]
        hh = ch.hh
        hv, hf = ico(hb + Vector((0, 0.18 * hh, 0.25 * hh)), 0.55 * hh, 1.0, 0.85, 0.75, 1)
        hf = [fc for fc in hf if sum(hv[k].y for k in fc) / 3 > hb.y + 0.05 * hh or sum(hv[k].z for k in fc) / 3 < hb.z + 0.1 * hh]
        m.add(hv, hf, shade(color, 0.92), [[('neck', 0.6), ('chest', 0.4)]] * len(hv), rng=ch.r)


def shoulder_pads(ch, m, color, size=1.0, spikes=False):
    for s in 'LR':
        h = ch.J[f'upper_arm.{s}'][0]
        k = ch.H / 1.75 * size * ch.bulk ** 0.5
        v, f = ico(h + Vector((0, 0, 0.02 * k)), 0.085 * k, 1.15, 1.1, 0.65, 0)
        v = [p for p in v]
        m.add(v, f, color, [[(f'upper_arm.{s}', 0.6), ('chest', 0.4)]] * len(v), rng=ch.r)


def bracers(ch, m, color):
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s, 1.3, 1.25, 1.9), color, cap_end=True, cap_start=True)


def satchel(ch, m, color, strap):
    H = ch.H
    s = ch.r.choice([-1, 1])
    side = 'L' if s > 0 else 'R'
    z = ch.hip_z - 0.02 * H
    tr = ch.torso_rings()
    rx = tr[1][1]
    c = Vector((s * (rx + 0.03 * H), 0.0, z))
    v, f = box(c, 0.05 * H, 0.12 * H, 0.1 * H)
    m.add(v, f, color, [[('hips', 0.7), (f'thigh.{side}', 0.3)]] * 8, rng=ch.r)
    fv, ff = box(c + Vector((s * 0.026 * H, 0, 0.03 * H)), 0.006 * H, 0.12 * H, 0.05 * H)
    m.add(fv, ff, shade(color, 0.8), 'hips', rng=ch.r)
    sash(ch, m, strap, side=-s, width=0.014)


def apron(ch, m, color, length=0.55):
    H = ch.H
    tr = ch.torso_rings()
    c, rx, ry, _ = tr[1]
    z0 = ch.hip_z + 0.03 * H
    z1 = ch.hip_z - length * ch.hip_z
    v = [Vector((-rx * 0.8, c.y - ry * 1.25, z0)), Vector((rx * 0.8, c.y - ry * 1.25, z0)),
         Vector((rx * 0.9, c.y - ry * 1.6, z1)), Vector((-rx * 0.9, c.y - ry * 1.6, z1))]
    W = [[('hips', 1.0)], [('hips', 1.0)], [('thigh.L', 0.6), ('hips', 0.4)], [('thigh.R', 0.6), ('hips', 0.4)]]
    m.add(v, [(0, 1, 2, 3)], color, W, rng=ch.r)
    m.add(v, [(3, 2, 1, 0)], shade(color, 0.8), W, rng=ch.r)


def necklace(ch, m, color, n=9):
    H = ch.H
    c = ch.J['neck'][0]
    for k in range(n):
        a = math.pi * (0.15 + 0.7 * k / (n - 1))
        p = c + Vector((math.cos(a) * 0.06 * H, -math.sin(a) * 0.05 * H - 0.01 * H, -0.03 * H - math.sin(a) * 0.035 * H))
        v, f = ico(p, 0.009 * H)
        m.add(v, f, color if k % 2 else P['gold'], 'chest', rng=ch.r)


def harness(ch, m, color):
    sash(ch, m, color, 1, 0.022)
    sash(ch, m, color, -1, 0.022)


# ================================================================================================ props (held items)
def grip_frame(ch, s):
    h, t = ch.J[f'hand.{s}']
    d = (t - h)
    x, z = bone_axes(d)
    grip = h + d * 0.5
    up = -z       # see module docstring: -Z of the hand is "up" when the forearm is raised forward
    return grip, up, d.normalized(), x


def prop_mesh(kind, ch, s):
    """Returns (verts, faces, colours per face, mats) in world rest space, gripped by hand s."""
    g, up, d, x = grip_frame(ch, s)
    H = ch.H
    m = CMesh()
    k = H / 1.75
    if kind in ('staff', 'spear', 'cane'):
        L = {'staff': 1.75, 'spear': 2.0, 'cane': 0.95}[kind] * k
        low = 0.62 * L if kind != 'cane' else 0.85 * L
        a, b = g - up * low, g + up * (L - low)
        R = [ring(a, up, 0.016 * k, 0.016 * k, 5), ring(b, up, 0.014 * k, 0.014 * k, 5)]
        v, f = loft(R, True, True)
        m.add(v, f, P['wood'], 'x')
        if kind == 'spear':
            v, f = cone(b, b + up * 0.24 * k, 0.035 * k, 4)
            m.add(v, f, P['steel'], 'x')
        elif kind == 'staff':
            v, f = ico(b + up * 0.07 * k, 0.06 * k, 1, 1, 1.4)
            m.add(v, f, P['glowc'], 'x', mat='CharGlow')
            for o in range(3):
                a2 = o * 2.09
                p = b + (x * math.cos(a2) + up.cross(x) * math.sin(a2)) * 0.06 * k
                v, f = cone(b - up * 0.02 * k, p + up * 0.14 * k, 0.012 * k, 3)
                m.add(v, f, P['bronze'], 'x')
        else:
            v, f = box(b, 0.12 * k, 0.03 * k, 0.03 * k)
            m.add(v, f, P['wood'], 'x')
    elif kind == 'hammer':
        a, b = g - up * 0.12 * k, g + up * 0.5 * k
        v, f = loft([ring(a, up, 0.018 * k, 0.018 * k, 5), ring(b, up, 0.018 * k, 0.018 * k, 5)], True, True)
        m.add(v, f, P['wood'], 'x')
        fwd = up.cross(x).normalized()
        v, f = box(b, 0.1 * k, 0.1 * k, 0.1 * k, Matrix((x * 1.0, fwd * 2.0, up * 1.0)).transposed())
        m.add(v, f, P['steel'], 'x')
    elif kind == 'blade':
        a = g - up * 0.08 * k
        b = g + up * 0.06 * k
        v, f = loft([ring(a, up, 0.016 * k, 0.016 * k, 5), ring(b, up, 0.016 * k, 0.016 * k, 5)], True, True)
        m.add(v, f, P['dleather'], 'x')
        v, f = box(b, 0.12 * k, 0.03 * k, 0.02 * k, Matrix((x, up.cross(x), up)).transposed())
        m.add(v, f, P['bronze'], 'x')
        fwd = up.cross(x).normalized()
        bl = [b + x * 0.025 * k, b - x * 0.025 * k, b + up * 0.62 * k]
        v = bl + [p + fwd * 0.008 * k for p in bl]
        f = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
        m.add(v, f, P['silver'], 'x')
    elif kind == 'lantern':   # hangs below the hand
        top = g + d * 0.08 * k
        bot = top + d * 0.2 * k
        v, f = loft([ring(top, d, 0.004 * k, 0.004 * k, 3), ring(top + d * 0.06 * k, d, 0.004 * k, 0.004 * k, 3)])
        m.add(v, f, P['dleather'], 'x')
        v, f = ico(top + d * 0.15 * k, 0.06 * k, 1, 1, 1.3, 0)
        m.add(v, f, P['glowy'], 'x', mat='CharGlow')
        v, f = box(top + d * 0.07 * k, 0.09 * k, 0.09 * k, 0.025 * k)
        m.add(v, f, P['bronze'], 'x')
    elif kind == 'tablet':
        fwd = up.cross(x).normalized()
        v, f = box(g + up * 0.08 * k, 0.16 * k, 0.012 * k, 0.22 * k, Matrix((x, fwd, up)).transposed())
        m.add(v, f, P['slate'], 'x')
        v, f = box(g + up * 0.08 * k - fwd * 0.008 * k, 0.12 * k, 0.004 * k, 0.17 * k, Matrix((x, fwd, up)).transposed())
        m.add(v, f, P['glowc'], 'x', mat='CharGlow')
    elif kind == 'pick':
        a, b = g - up * 0.15 * k, g + up * 0.6 * k
        v, f = loft([ring(a, up, 0.017 * k, 0.017 * k, 5), ring(b, up, 0.017 * k, 0.017 * k, 5)], True, True)
        m.add(v, f, P['wood'], 'x')
        fwd = up.cross(x).normalized()
        v, f = cone(b, b + fwd * 0.22 * k - up * 0.05 * k, 0.03 * k, 4)
        m.add(v, f, P['steel'], 'x')
        v, f = cone(b, b - fwd * 0.12 * k, 0.025 * k, 4)
        m.add(v, f, P['steel'], 'x')
    return m


# ================================================================================================ species builders
def build_human(ch, m):
    r = ch.r
    skin = ch.skin
    hair = hexc(r.choice(HAIR))
    if ch.age == 'elder':
        hair = hexc(r.choice(['#c8c4bc', '#a8a49c', '#e0dcd4']))
    c1, c2, c3 = ch.colors
    head = Head(ch, HEADS['human'])
    # body
    ch.build_torso(m, skin)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s), skin)
        ch.tube(m, ch.leg_rings(s), skin)
        ch.build_hand(m, s, skin)
    neck_r = 0.034 * ch.H * ch.bulk ** 0.5
    ch.tube(m, [(ch.J['neck'][0] - Vector((0, 0, 0.01 * ch.H)), Vector((0, 0, 1)), neck_r, [('neck', 1.0)]),
                (ch.J['neck'][1] + Vector((0, 0, 0.02 * ch.H)), Vector((0, 0, 1)), neck_r * 0.95, [('head', 1.0)])], skin)
    jaw = r.uniform(0.9, 1.15)
    head.prof = [(t, w * (jaw if t < 0.3 else 1.0), d, y) for t, w, d, y in head.prof]
    head.build(m, skin)
    # face
    eye_c = hexc(r.choice(['#4a3020', '#2a5a7a', '#3a6a3a', '#6a4a2a', '#5a6a7a', '#2a2018']))
    es = r.uniform(0.085, 0.1) * (1.25 if ch.age == 'young' else 1.0)
    sep = r.uniform(0.36, 0.42)
    for xs in (-1, 1):
        eye(m, head, 0.56, xs * sep, es, ch, eye_c, tilt=r.uniform(-0.1, 0.15))
        brow(m, head, 0.67, xs * sep, 0.24, ch, shade(hair, 0.8), angle=r.uniform(-0.25, 0.3))
        p, n = head.surf(0.5, xs * 0.98, -0.02)   # ears
        v, f = ico(p + Vector((xs * 0.02 * ch.hh, 0.02 * ch.hh, 0)), 0.11 * ch.hh, 0.4, 0.7, 1.0)
        m.add(v, f, shade(skin, 0.92), 'head', rng=r)
    nose(m, head, 0.47, ch, skin, r.uniform(0.09, 0.15), r.uniform(0.07, 0.11), r.uniform(0.14, 0.2), 0.0)
    mouth(m, head, 0.27, r.uniform(0.22, 0.3), ch, '#5a2e28', smile=r.uniform(-0.2, 0.6))
    # hair
    style = r.choice(['crop', 'long', 'bun', 'curly', 'braid', 'shaved', 'crop'])
    if ch.age == 'elder' and r.random() < 0.5:
        style = 'thin'
    if style != 'shaved':
        hair_cap(m, ch, head, hair, front_t=0.78 if style != 'thin' else 0.9,
                 back_t=0.42 if style != 'thin' else 0.55, fringe=r.uniform(0, 0.08))
    hb = head.base
    hh = head.hh
    if style == 'long':
        v, f = box(hb + Vector((0, 0.42 * hh, 0.15 * hh)), 0.9 * hh, 0.22 * hh, 0.95 * hh)
        m.add(v, f, hair, [[('head', 0.6), ('neck', 0.4)]] * 8, rng=r)
    elif style == 'bun':
        v, f = ico(hb + Vector((0, 0.55 * hh, 0.85 * hh)), 0.2 * hh, 1, 1, 0.9, 1)
        m.add(v, f, hair, 'head', rng=r)
    elif style == 'curly':
        for k in range(14):
            a = r.uniform(0, 6.28)
            t = r.uniform(0.55, 1.0)
            w, d, yo = head.at(t)
            p = hb + Vector((math.sin(a) * w * hh * 1.05, yo * hh + (-math.cos(a)) * d * hh * 1.05, t * hh))
            if p.y < hb.y - 0.2 * hh and t < 0.82:
                continue
            v, f = ico(p, r.uniform(0.12, 0.18) * hh)
            m.add(v, f, hair, 'head', rng=r)
    elif style == 'braid':
        path = [hb + Vector((0, 0.5 * hh, 0.5 * hh)), hb + Vector((0, 0.62 * hh, 0.0)), hb + Vector((0, 0.66 * hh, -0.6 * hh))]
        R = [ring(p, Vector((0, 0.1, -1)), 0.1 * hh, 0.1 * hh, 5) for p in path]
        v, f = loft(R, False, True)
        m.add(v, f, hair, [[('head', 0.7), ('neck', 0.3)]] * 5 + [[('neck', 0.5), ('chest', 0.5)]] * 10, rng=r)
    if not ch.fem and ch.age != 'young' and r.random() < 0.45:   # beard
        p, n = head.surf(0.12, 0, 0.02)
        v, f = ico(p + Vector((0, 0.02 * hh, 0.04 * hh)), 0.3 * hh, 1.4, 0.8, 0.9)
        m.add(v, f, hair, 'head', rng=r)
    # clothing: practical, layered, planet-made
    outfit = r.choice(['tunic', 'coat', 'robe', 'vest'])
    if ch.age == 'young':
        outfit = 'tunic'
    trousers(ch, m, shade(c2, 0.85))
    if outfit == 'tunic':
        shirt(ch, m, c1, 'long' if r.random() < 0.6 else 'short')
        skirt(ch, m, c1, 0.35, 1.25)
        belt(ch, m, P['leather'], 0.13, P['bronze'])
    elif outfit == 'coat':
        shirt(ch, m, c3, 'long')
        skirt(ch, m, c1, 0.55, 1.35, 0.4)
        shirt(ch, m, c1, 'short', 0.4, 0.95, scale=1.12)
        belt(ch, m, P['dleather'], 0.12, P['gold'])
    elif outfit == 'robe':
        shirt(ch, m, c1, 'long', collar=c2)
        skirt(ch, m, c1, 0.92, 1.5)
        sash(ch, m, c3)
    else:
        shirt(ch, m, c3, 'long')
        shirt(ch, m, c1, 'none', 0.15, 0.95, scale=1.12)
        belt(ch, m, P['leather'], 0.1)
    boots(ch, m, P['dleather'] if r.random() < 0.6 else P['leather'], r.uniform(0.3, 0.6))
    if r.random() < 0.45:
        scarf(ch, m, c3)
    if r.random() < 0.3 and outfit != 'robe':
        cape(ch, m, shade(c2, 0.9), 0.7, hood=r.random() < 0.4)
    if r.random() < 0.5:
        satchel(ch, m, P['leather'], P['dleather'])


def build_avari(ch, m):
    r = ch.r
    skin = ch.skin
    c1, c2, c3 = ch.colors
    head = Head(ch, HEADS['avari'])
    ch.build_torso(m, skin)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s), skin)
        ch.tube(m, ch.leg_rings(s), skin)
        ch.build_hand(m, s, skin)
    nr = 0.025 * ch.H
    ch.tube(m, [(ch.J['neck'][0] - Vector((0, 0, 0.01 * ch.H)), Vector((0, 0, 1)), nr, [('neck', 1.0)]),
                (ch.J['neck'][1] + Vector((0, 0, 0.02 * ch.H)), Vector((0, 0, 1)), nr * 0.9, [('head', 1.0)])], skin)
    head.build(m, skin)
    hh = head.hh
    # large dark almond eyes, slanted
    es = r.uniform(0.13, 0.15)
    for xs in (-1, 1):
        eye(m, head, 0.5, xs * 0.42, es, ch, hexc(r.choice(['#14121e', '#1e1830', '#101a24'])), sclera=False,
            almond=1.45, tilt=0.35)
        # temple ridges: three short ridges sweeping back
        for k in range(3):
            p, n = head.surf(0.56 + k * 0.08, xs * 0.97, 0.0)
            a = p
            b = p + Vector((0, 0.18 * hh, 0.05 * hh))
            R = [ring(a, b - a, 0.025 * hh, 0.012 * hh, 4), ring(b, b - a, 0.008 * hh, 0.004 * hh, 4)]
            v, f = loft(R, True, True)
            m.add(v, f, shade(skin, 0.85), 'head', rng=r)
        brow(m, head, 0.64, xs * 0.42, 0.22, ch, shade(skin, 0.82), angle=r.uniform(0.0, 0.3), thick=0.02)
    nose(m, head, 0.4, ch, skin, 0.06, 0.05, 0.2)
    mouth(m, head, 0.22, 0.18, ch, '#4a3a5a', smile=r.uniform(-0.1, 0.4))
    # hair: none, long silver fall, or a head-wrap
    style = r.choice(['bare', 'silver', 'wrap', 'silver'])
    if style == 'silver':
        hc = hexc(r.choice(['#e6e6f0', '#c8c8dc', '#2a2840', '#9a8ac0']))
        hair_cap(m, ch, head, hc, 0.84, 0.45)
        v, f = box(head.base + Vector((0, 0.52 * hh, 0.0)), 0.7 * hh, 0.16 * hh, 1.3 * hh)
        m.add(v, f, hc, [[('head', 0.5), ('neck', 0.5)]] * 8, rng=r)
    elif style == 'wrap':
        hair_cap(m, ch, head, c2, 0.86, 0.5, scale=1.12)
    # circlet with a glyph-stone (heirs of the ring-shrine builders)
    if r.random() < 0.7:
        t = 0.74
        w, d, yo = head.at(t)
        c = head.base + Vector((0, yo * hh, t * hh))
        R = [ring(c, Vector((0, 0, 1)), w * hh * 1.08, d * hh * 1.08, 10),
             ring(c + Vector((0, 0, 0.04 * hh)), Vector((0, 0, 1)), w * hh * 1.08, d * hh * 1.08, 10)]
        v, f = loft(R)
        m.add(v, f, P['silver'], 'head', rng=r)
        p, n = head.surf(t + 0.02, 0, 0.1)
        v, f = disc(p, n, Vector((0, 0, 1)), 0.05 * hh, 0.07 * hh, 4, 0.02 * hh)
        m.add(v, f, P['glowc'], 'head', mat='CharGlow', rng=r)
    # flowing robes with high collars and glyph-lit hems
    shirt(ch, m, c1, 'long', collar=c2)
    skirt(ch, m, c1, 0.95, 1.5, hem=P['glowc'] if r.random() < 0.6 else c2)
    sash(ch, m, c3, 1, 0.03)
    if r.random() < 0.6:
        cape(ch, m, c2, 0.9, hood=r.random() < 0.3, trim=c3)
    for s in 'LR':
        ch.build_foot(m, s, shade(c2, 0.7), 1.0)


def build_keth(ch, m):
    r = ch.r
    skin = ch.skin
    scale_hi = mix(skin, hexc('#d8c890'), 0.25)
    belly = mix(skin, hexc('#d8c8a0'), 0.45)
    c1, c2, c3 = ch.colors

    def scales(fi, cen, n):   # subtle scale pattern: alternating facets, lighter belly
        c = skin if (fi % 3) else scale_hi
        if n.y < -0.6 and abs(cen.x) < 0.1 * ch.H:
            c = belly
        return c
    head = Head(ch, HEADS['keth'])
    ch.build_torso(m, scales)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s), scales)
        ch.tube(m, ch.leg_rings(s), scales)
        ch.build_hand(m, s, skin)
    nr = 0.05 * ch.H
    ch.tube(m, [(ch.J['neck'][0] - Vector((0, 0, 0.01 * ch.H)), Vector((0, 0, 1)), nr, [('neck', 1.0)]),
                (ch.J['neck'][1] + Vector((0, 0, 0.03 * ch.H)), Vector((0, 0, 1)), nr * 0.95, [('head', 1.0)])], scales)
    head.build(m, scales)
    hh = head.hh
    # deep-set amber eyes with slit pupils under a heavy brow
    eye_c = hexc(r.choice(['#d8a030', '#c8b040', '#d07028', '#a8c050']))
    for xs in (-1, 1):
        eye(m, head, 0.56, xs * 0.38, 0.075, ch, eye_c, slit=True, tilt=0.05, out=-0.005)
        p, n = head.surf(0.66, xs * 0.38, 0.02)
        a, b = p - Vector((xs * 0.18 * hh, 0, -0.02 * hh)), p + Vector((xs * 0.2 * hh, 0, 0.03 * hh))
        R = [ring(a, b - a, 0.05 * hh, 0.035 * hh, 4), ring(b, b - a, 0.035 * hh, 0.025 * hh, 4)]
        v, f = loft(R, True, True)
        m.add(v, f, shade(skin, 0.85), 'head', rng=r)
        # jaw ridge
        p, n = head.surf(0.2, xs * 0.85, 0.0)
        v, f = cone(p, p + Vector((xs * 0.08 * hh, 0.1 * hh, -0.02 * hh)), 0.04 * hh, 4)
        m.add(v, f, shade(skin, 0.8), 'head', rng=r)
    # bony head ridges along the crown
    nr_ = r.randint(3, 5)
    for k in range(nr_):
        t = 0.78 + k * 0.05
        w, d, yo = head.at(min(t, 1.0))
        p = head.base + Vector((0, (yo - d * 0.4 + k * 0.22) * hh, min(t, 1.0) * hh + 0.02 * hh))
        v, f = cone(p, p + Vector((0, 0.1 * hh, 0.14 * hh * (1.2 - k * 0.15))), 0.06 * hh, 4)
        m.add(v, f, mix(skin, hexc('#e0d0a8'), 0.35), 'head', rng=r)
    nose(m, head, 0.42, ch, skin, 0.08, 0.12, 0.12)
    mouth(m, head, 0.22, 0.42, ch, '#3a2420', smile=r.uniform(-0.3, 0.3))
    # work gear: leather, bronze, heavy boots
    trousers(ch, m, shade(c1, 0.8))
    style = r.choice(['harness', 'apron', 'vest', 'armour'])
    if style == 'harness':
        harness(ch, m, P['dleather'])
        belt(ch, m, P['leather'], 0.12, P['bronze'])
    elif style == 'apron':
        shirt(ch, m, c2, 'short')
        apron(ch, m, P['leather'], 0.6)
        belt(ch, m, P['dleather'], 0.12)
    elif style == 'vest':
        shirt(ch, m, c2, 'none', 0.1, 0.95, scale=1.08)
        belt(ch, m, P['dleather'], 0.1, P['bronze'])
        skirt(ch, m, c3, 0.4, 1.2)
    else:
        shirt(ch, m, c2, 'short')
        shoulder_pads(ch, m, P['bronze'])
        belt(ch, m, P['dleather'], 0.12, P['gold'])
        skirt(ch, m, P['leather'], 0.35, 1.25)
    if r.random() < 0.6:
        bracers(ch, m, P['leather'])
    boots(ch, m, P['dleather'], 0.55)


def build_luma(ch, m):
    r = ch.r
    skin = ch.skin
    glow = P[r.choice(['glowc', 'glowg', 'glowp', 'glowy'])]
    c1, c2, c3 = ch.colors
    head = Head(ch, HEADS['luma'])
    soft = mix(skin, hexc('#ffffff'), 0.15)

    def smooth_skin(fi, cen, n):   # translucent look: brighter toward edges facing away (cheap fake SSS)
        return mix(skin, soft, clamp(0.5 - n.y * 0.5))
    ch.build_torso(m, smooth_skin)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s), smooth_skin)
        ch.tube(m, ch.leg_rings(s), smooth_skin)
        ch.build_hand(m, s, skin)
    nr = 0.026 * ch.H
    ch.tube(m, [(ch.J['neck'][0] - Vector((0, 0, 0.01 * ch.H)), Vector((0, 0, 1)), nr, [('neck', 1.0)]),
                (ch.J['neck'][1] + Vector((0, 0, 0.02 * ch.H)), Vector((0, 0, 1)), nr * 0.9, [('head', 1.0)])], smooth_skin)
    head.build(m, smooth_skin)
    hh = head.hh
    for xs in (-1, 1):   # luminous eyes
        eye(m, head, 0.52, xs * 0.38, 0.1, ch, glow, sclera=False, glow=True, almond=1.3, tilt=0.2)
        # cheek & brow light markings
        for k in range(3):
            p, n = head.surf(0.36 - k * 0.07, xs * (0.55 + k * 0.08), 0.008)
            v, f = disc(p, n, Vector((xs * 0.4, 0, 1)), 0.035 * hh, 0.012 * hh, 4)
            m.add(v, f, glow, 'head', mat='CharGlow', rng=r)
        p, n = head.surf(0.66, xs * 0.4, 0.01)
        v, f = disc(p, n, Vector((xs * -0.5, 0, 1)), 0.1 * hh, 0.014 * hh, 4)
        m.add(v, f, glow, 'head', mat='CharGlow', rng=r)
    nose(m, head, 0.42, ch, skin, 0.05, 0.05, 0.12)
    mouth(m, head, 0.24, 0.2, ch, '#7a5a6a', smile=r.uniform(0.0, 0.6))
    # two soft back-swept lobes from the crown: the Luma silhouette
    for xs in (-1, 1):
        p, n = head.surf(0.86, xs * 0.45, -0.1)
        tip = p + Vector((xs * 0.12 * hh, 0.75 * hh, -0.15 * hh))
        R = [ring(p, tip - p, 0.16 * hh, 0.1 * hh, 6), ring(p + (tip - p) * 0.6, tip - p, 0.09 * hh, 0.06 * hh, 6)]
        v, f = loft(R, True, False)
        v.append(tip)
        f += [(6 + k, 6 + (k + 1) % 6, 12) for k in range(6)]
        m.add(v, f, smooth_skin, 'head', rng=r)
        q = p + (tip - p) * 0.45 + Vector((0, 0, 0.1 * hh))
        gv, gf = disc(q, Vector((xs * 0.3, 0.2, 1)), tip - p, 0.03 * hh, 0.22 * hh, 4)
        m.add(gv, gf, glow, 'head', mat='CharGlow', rng=r)
    # crown line markings
    for k in range(5):
        t = 0.72 + k * 0.06
        p, n = head.surf(min(t, 1.0), 0, 0.01)
        v, f = disc(p + Vector((0, (k * 0.1) * hh, 0)), Vector((0, -0.3, 1)), Vector((0, 1, 0)), 0.02 * hh, 0.06 * hh, 4)
        m.add(v, f, glow, 'head', mat='CharGlow', rng=r)
    # glowing lines beneath the skin of the arms, legs and chest
    pattern = r.choice(['lines', 'dots', 'spiral'])
    for s in 'LR':
        for bname in (f'upper_arm.{s}', f'forearm.{s}', f'thigh.{s}', f'shin.{s}'):
            h, t = ch.J[bname]
            dvec = t - h
            x, z = bone_axes(dvec)
            rad = 0.05 * ch.H / 1.75 * ch.bulk * (1.5 if 'thigh' in bname else 1.0)
            for k in range(3 if pattern != 'lines' else 1):
                u = 0.25 + 0.25 * k if pattern != 'lines' else 0.5
                p = h + dvec * u - z * rad * 1.02
                if pattern == 'lines':
                    v, f = disc(p, -z, dvec, 0.011 * ch.H, dvec.length * 0.4, 4)
                else:
                    v, f = disc(p, -z, dvec, 0.017 * ch.H, 0.017 * ch.H * (1.8 if pattern == 'spiral' else 1.0), 6)
                m.add(v, f, glow, bname, mat='CharGlow', rng=r)
    for k in range(4):
        p = Vector((0, -ch.torso_rings()[3][2] * 1.03, lerp(ch.hip_z, ch.neck_base, 0.55 + k * 0.1)))
        v, f = disc(p, Vector((0, -1, 0)), Vector((0, 0, 1)), 0.012 * ch.H * (2 - k * 0.3), 0.008 * ch.H, 4)
        m.add(v, f, glow, 'chest', mat='CharGlow', rng=r)
    # light wraps and sashes: leave glowing skin visible
    style = r.choice(['wrap', 'gown', 'sash'])
    if style == 'wrap':
        ch.build_torso(m, c1, 1.07, 0.55, 0.9, cap=False)
        skirt(ch, m, c1, 0.6, 1.3)
    elif style == 'gown':
        shirt(ch, m, c1, 'none', 0.0, 0.88)
        skirt(ch, m, c1, 0.9, 1.4, hem=c3)
    else:
        trousers(ch, m, c2, 1.6, 1.15)
        sash(ch, m, c1, 1, 0.06)
        belt(ch, m, c3, 0.1)
    if r.random() < 0.5:
        scarf(ch, m, c3, tail=True)
    for s in 'LR':
        ch.build_foot(m, s, shade(c2, 0.8), 1.0)


def build_vorn(ch, m):
    r = ch.r
    skin = ch.skin
    shell = hexc(r.choice(['#2e3a3e', '#4a2e3a', '#3a3a2a', '#5a3a24', '#26303a']))
    shell_hi = mix(shell, hexc('#c8b070'), 0.25)
    c1, c2, c3 = ch.colors
    head = Head(ch, HEADS['vorn'])

    def carapace(fi, cen, n):
        return shell_hi if n.z > 0.5 else shell
    ch.build_torso(m, skin)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s), skin)
        ch.tube(m, ch.leg_rings(s), skin)
        ch.build_hand(m, s, shade(shell, 1.2))
    nr = 0.03 * ch.H
    ch.tube(m, [(ch.J['neck'][0] - Vector((0, 0, 0.01 * ch.H)), Vector((0, 0, 1)), nr, [('neck', 1.0)]),
                (ch.J['neck'][1] + Vector((0, 0, 0.02 * ch.H)), Vector((0, 0, 1)), nr * 0.9, [('head', 1.0)])], skin)
    head.build(m, skin)
    hh = head.hh
    # exoskeleton plates: segmented over chest, back, shoulders, forearms and shins
    # segmented chest/back carapace: three overlapping bands
    for t0, t1, k in ((0.5, 0.66, 1.08), (0.64, 0.8, 1.11), (0.78, 0.95, 1.12)):
        ch.build_torso(m, carapace, k, t0, t1, cap=False)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s, 1.22, 1.15, 1.85), carapace, cap_end=True, cap_start=True)
        ch.tube(m, ch.arm_rings(s, 1.25, 0.05, 0.6), carapace, cap_end=True, cap_start=True)
        ch.tube(m, ch.leg_rings(s, 1.2, 1.15, 1.9), carapace, cap_end=True, cap_start=True)
        shoulder_pads(ch, m, carapace, 0.9)
    # head plates: crown shell split down the middle
    hair_cap(m, ch, head, lambda fi, cen, n: shell_hi if fi % 10 in (0, 5) else shell, 0.82, 0.5, scale=1.08)
    # multiple eyes: two large, plus a smaller pair above (some have three pairs)
    eye_c = hexc(r.choice(['#1a1a20', '#20140e', '#101820']))
    glint = hexc(r.choice(['#d8a030', '#60c090', '#c06060', '#a0a0e0']))
    for xs in (-1, 1):
        eye(m, head, 0.5, xs * 0.36, 0.1, ch, eye_c, sclera=False, almond=1.1)
        eye(m, head, 0.68, xs * 0.26, 0.055, ch, eye_c, sclera=False)
        if r.random() < 0.5:
            eye(m, head, 0.62, xs * 0.6, 0.045, ch, eye_c, sclera=False)
        p, n = head.surf(0.5, xs * 0.36, 0.06)
        v, f = disc(p, n, Vector((0, 0, 1)), 0.03 * hh, 0.02 * hh, 4)
        m.add(v, f, glint, 'head', rng=r)
        brow(m, head, 0.6, xs * 0.36, 0.26, ch, shell, angle=r.uniform(-0.3, 0.35), thick=0.04)
        # mouth palps: short sensory feelers beside the mouth
        p, n = head.surf(0.24, xs * 0.45, 0.0)
        v, f = cone(p, p + Vector((xs * 0.05 * hh, -0.12 * hh, -0.12 * hh)), 0.03 * hh, 4)
        m.add(v, f, shade(skin, 0.8), 'head', rng=r)
    mouth(m, head, 0.27, 0.26, ch, '#3a1e24', smile=r.uniform(-0.2, 0.5), lips=shade(skin, 0.85))
    # antennae (sensory appendages) with their own bones
    for s, xs in (('L', 1), ('R', -1)):
        p, n = head.surf(0.92, xs * 0.3, 0.0)
        tip = p + Vector((xs * 0.25 * hh, 0.15 * hh, 0.75 * hh))
        ch.add_bone(f'antenna.{s}', p, tip, 'head')
        mid = (p + tip) / 2 + Vector((0, -0.08 * hh, 0.05 * hh))
        R = [ring(p, tip - p, 0.03 * hh, 0.03 * hh, 4), ring(mid, tip - p, 0.02 * hh, 0.02 * hh, 4),
             ring(tip, tip - p, 0.012 * hh, 0.012 * hh, 4)]
        v, f = loft(R, False, True)
        W = [[('head', 1.0)]] * 4 + [[(f'antenna.{s}', 1.0)]] * 8
        m.add(v, f, shell, W, rng=r)
        v, f = ico(tip, 0.04 * hh, 1, 1, 1.5)
        m.add(v, f, glint, f'antenna.{s}', rng=r)
    # cloth wraps over the soft waist, tool belts over the carapace
    trousers(ch, m, c1, 1.1, 1.14)
    ch.build_torso(m, c2, 1.12, 0.05, 0.52, cap=False)
    skirt(ch, m, c2, 0.4, 1.25)
    belt(ch, m, P['dleather'], 0.12, P['bronze'])
    if r.random() < 0.7:
        satchel(ch, m, c3, P['dleather'])
    if r.random() < 0.5:
        scarf(ch, m, c3)
    for s in 'LR':
        ch.build_foot(m, s, shade(shell, 1.1), 1.0)


def build_murrai(ch, m):
    r = ch.r
    fur = ch.skin
    mark = hexc(r.choice(['#2a2228', '#4a3020', '#e8dcc0', '#3a4050', '#7a3a2a']))
    belly = mix(fur, hexc('#efe4cc'), 0.55)
    pattern = r.choice(['stripes', 'spots', 'saddle', 'bands'])
    c1, c2, c3 = ch.colors

    def furc(fi, cen, n):
        c = fur
        if n.y < -0.55 and abs(cen.x) < 0.08 * ch.H and cen.z > ch.hip_z * 0.9:
            c = belly
        if pattern == 'stripes' and math.sin(cen.z * 38 + cen.x * 12) > 0.55 and n.y > -0.5:
            c = mark
        elif pattern == 'spots' and math.sin(cen.x * 55) * math.sin(cen.z * 47) > 0.55:
            c = mark
        elif pattern == 'saddle' and n.y > 0.3 and cen.z > ch.hip_z:
            c = mix(fur, mark, 0.7)
        elif pattern == 'bands' and (fi // 6) % 4 == 0:
            c = mix(fur, mark, 0.6)
        return c
    head = Head(ch, HEADS['murrai'])
    ch.build_torso(m, furc)
    for s in 'LR':
        ch.tube(m, ch.arm_rings(s), furc)
        ch.tube(m, ch.leg_rings(s), furc)
        ch.build_hand(m, s, shade(fur, 0.8))
        ch.build_foot(m, s, shade(fur, 0.75), 1.0)
    nr = 0.045 * ch.H
    ch.tube(m, [(ch.J['neck'][0] - Vector((0, 0, 0.01 * ch.H)), Vector((0, 0, 1)), nr, [('neck', 1.0)]),
                (ch.J['neck'][1] + Vector((0, 0, 0.02 * ch.H)), Vector((0, 0, 1)), nr * 0.95, [('head', 1.0)])], furc)
    head.build(m, lambda fi, cen, n: belly if (n.y < -0.7 and cen.z < head.base.z + 0.45 * head.hh) else fur)
    hh = head.hh
    # short broad muzzle with a split nose pad (not a dog or cat: flat, wide, with a ridge line)
    p, n = head.surf(0.3, 0, 0.0)
    v, f = ico(p + Vector((0, -0.08 * hh, 0)), 0.22 * hh, 1.25, 0.8, 0.75, 1)
    m.add(v, f, belly, 'head', rng=r)
    # flat bar-shaped nose pad with three nostril slits (no animal snout)
    q = p + Vector((0, -0.25 * hh, 0.07 * hh))
    v, f = box(q, 0.2 * hh, 0.05 * hh, 0.05 * hh)
    m.add(v, f, hexc('#2a1e22'), 'head', rng=r)
    mouth(m, head, 0.18, 0.2, ch, '#2a1a1e', out=0.18, smile=r.uniform(0.0, 0.7))
    # big expressive eyes and a facial mask marking
    eye_c = hexc(r.choice(['#e0b040', '#60c0a0', '#a070e0', '#d07040']))
    for xs in (-1, 1):
        p, n = head.surf(0.52, xs * 0.42, 0.006)
        v, f = disc(p, n, Vector((xs * 0.5, 0, 1)), 0.2 * hh, 0.12 * hh, 6)
        m.add(v, f, mix(fur, mark, 0.8), 'head', rng=r)
        eye(m, head, 0.53, xs * 0.42, 0.12, ch, eye_c, almond=1.1, tilt=0.15, out=0.02)
        brow(m, head, 0.66, xs * 0.4, 0.22, ch, mark, angle=r.uniform(-0.2, 0.4), thick=0.04)
        # cheek ruffs
        for k in range(3):
            p, n = head.surf(0.3 + k * 0.08, xs * 0.95, -0.02)
            v, f = cone(p, p + Vector((xs * (0.16 - k * 0.03) * hh, 0.06 * hh, -0.06 * hh)), 0.06 * hh, 4)
            m.add(v, f, fur, 'head', rng=r)
    # long fin-like ears that sweep back from the sides of the head, with bones
    ear_len = r.uniform(0.9, 1.2) * hh
    droop = r.uniform(-0.15, 0.25)
    for s, xs in (('L', 1), ('R', -1)):
        p, n = head.surf(0.7, xs * 0.92, -0.06)
        tip = p + Vector((xs * ear_len * 0.45, ear_len * 0.8, ear_len * (0.35 - droop)))
        ch.add_bone(f'ear.{s}', p, tip, 'head')
        mid = p + (tip - p) * 0.45
        R = [ring(p, tip - p, 0.16 * hh, 0.05 * hh, 5), ring(mid, tip - p, 0.13 * hh, 0.04 * hh, 5)]
        v, f = loft(R, True, False)
        v += [tip]
        nn = 5
        f += [(nn + k, nn + (k + 1) % nn, 2 * nn) for k in range(nn)]
        W = [[('head', 1.0)]] * 5 + [[(f'ear.{s}', 1.0)]] * 6
        m.add(v, f, lambda fi, cen, n: mark if fi % 5 == 0 else fur, W, rng=r)
        tv, tf = cone(tip - (tip - p) * 0.05, tip + (tip - p).normalized() * 0.12 * hh, 0.05 * hh, 4)
        m.add(tv, tf, mark, f'ear.{s}', rng=r)
    # crest mane from the brow over the skull and down the nape
    for k in range(7):
        u = k / 6
        t = lerp(0.9, 0.35, u)
        w, d, yo = head.at(min(1.0, t + 0.08))
        p = head.base + Vector((0, (yo + lerp(-0.2, 0.75, u) * d) * hh, (min(1.0, t + 0.08) + 0.1 * (1 - u)) * hh))
        v, f = cone(p, p + Vector((0, 0.16 * hh, 0.14 * hh * (1.2 - u * 0.6))), 0.07 * hh, 4)
        m.add(v, f, mark, 'head' if u < 0.7 else (lambda i, q: [('head', 0.4), ('neck', 0.6)]), rng=r)
    # brow feelers: two soft whisker-tufts above the eyes
    for xs in (-1, 1):
        p, n = head.surf(0.72, xs * 0.55, 0.0)
        v, f = cone(p, p + Vector((xs * 0.2 * hh, -0.05 * hh, 0.18 * hh)), 0.025 * hh, 3)
        m.add(v, f, belly, 'head', rng=r)
    # tail: three bones, tufted tip
    base = Vector((0, ch.torso_rings()[1][2] * 0.9, ch.hip_z + 0.02 * ch.H))
    tl = ch.H * r.uniform(0.42, 0.55)
    curl = r.uniform(-0.2, 0.3)
    pts = [base]
    for k in range(3):
        u = (k + 1) / 3
        pts.append(base + Vector((curl * tl * u * u, tl * (0.3 + 0.35 * u) * u, -tl * 0.62 * u + tl * 0.35 * u * u)))
    for k in range(3):
        ch.add_bone(f'tail.{k + 1}', pts[k], pts[k + 1], 'hips' if k == 0 else f'tail.{k}')
    R, W = [], []
    rads = [0.05, 0.042, 0.034, 0.03]
    for k, p in enumerate(pts):
        dvec = pts[min(k + 1, 3)] - pts[max(k - 1, 0)]
        R.append(ring(p, dvec, rads[k] * ch.H, rads[k] * ch.H, 5))
        bn = 'hips' if k == 0 else f'tail.{k}'
        W += [[(bn, 1.0)]] * 5
    v, f = loft(R, True, False)
    m.add(v, f, lambda fi, cen, n: mark if (fi // 5) % 2 else fur, W, rng=r)
    tv, tf = ico(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.05 * ch.H, 0.06 * ch.H, 1, 1, 1.4)
    m.add(tv, tf, mark, 'tail.3', rng=r)
    # chest ruff, elbow tufts
    for k in range(5):
        a = math.pi * (0.2 + 0.6 * k / 4)
        p = ch.J['neck'][0] + Vector((math.cos(a) * 0.06 * ch.H, -math.sin(a) * 0.05 * ch.H, -0.04 * ch.H))
        v, f = cone(p, p + Vector((0, -0.04 * ch.H, -0.07 * ch.H)), 0.025 * ch.H, 4)
        m.add(v, f, belly, 'chest', rng=r)
    # clothing: vests, wraps, beads
    style = r.choice(['vest', 'wrap', 'shawl'])
    if style == 'vest':
        shirt(ch, m, c1, 'none', 0.3, 0.95, scale=1.1)
        skirt(ch, m, c2, 0.4, 1.25)
    elif style == 'wrap':
        sash(ch, m, c1, 1, 0.07)
        skirt(ch, m, c2, 0.55, 1.3)
    else:
        cape(ch, m, c1, 0.45)
        skirt(ch, m, c2, 0.45, 1.25)
    belt(ch, m, P['leather'], 0.12, P['gold'])
    if r.random() < 0.7:
        necklace(ch, m, c3)
    if r.random() < 0.4:
        satchel(ch, m, c3, P['leather'])


BUILDERS = dict(human=build_human, avari=build_avari, keth=build_keth, luma=build_luma, vorn=build_vorn,
                murrai=build_murrai)

PROPS = {   # what each individual carries in the right / left hand (None = nothing)
    'human': [('spear', None), ('pick', 'lantern'), (None, None), ('tablet', None), ('cane', None), (None, None)],
    'avari': [('staff', None), ('tablet', None), (None, 'lantern'), ('blade', None), ('staff', None)],
    'keth': [('hammer', None), ('pick', None), (None, None), ('spear', None), ('cane', None)],
    'luma': [(None, 'lantern'), ('staff', None), (None, None), ('tablet', None), ('cane', None)],
    'vorn': [('tablet', None), ('hammer', None), (None, 'lantern'), ('blade', None), ('cane', None)],
    'murrai': [('spear', None), (None, None), (None, None), ('blade', 'lantern'), ('staff', None)],
}


# ================================================================================================ animation
def pose_fns(ch, held_r, held_l):
    """Pose functions t(0..1) -> {bone: (rx, ry, rz), '_loc': hips offset}. +rx = backwards swing.
    Upper-arm rz brings the A-pose arms down (L: +, R: -)."""
    tail = [b for b in ch.extra_bones if b.startswith('tail')]
    ears = [b for b in ch.extra_bones if b.startswith(('ear', 'antenna'))]
    elder = ch.age == 'elder'
    hunch = 0.18 if elder else 0.0
    arm_down = 0.62

    def arms_base(p, swing=0.0, bend=-0.25, carry_r=held_r, carry_l=held_l):
        p['upper_arm.L'] = (swing, 0, arm_down)
        p['upper_arm.R'] = (-swing, 0, -arm_down)
        p['forearm.L'] = (bend, 0, 0)
        p['forearm.R'] = (bend, 0, 0)
        if carry_r and carry_r not in ('lantern',):
            p['upper_arm.R'] = (-0.25 - swing * 0.3, 0, -arm_down + 0.1)
            p['forearm.R'] = (-1.15, 0, 0)
            p['hand.R'] = (0.15, 0, 0)
        if carry_l and carry_l not in ('lantern',):
            p['upper_arm.L'] = (-0.25 + swing * 0.3, 0, arm_down - 0.1)
            p['forearm.L'] = (-1.15, 0, 0)

    def extras(p, t, amp=1.0, speed=1.0):
        for i, b in enumerate(tail):
            p[b] = (-0.25 + 0.12 * math.sin(2 * math.pi * (t * speed) - i * 0.8) * amp, 0,
                    0.3 * math.sin(2 * math.pi * t * speed - i * 0.9) * amp)
        for i, b in enumerate(ears):
            sg = 1 if b.endswith('L') else -1
            p[b] = (0.08 * math.sin(2 * math.pi * t * speed * 2 + i) * amp, 0, sg * 0.05 * math.sin(2 * math.pi * t * speed) * amp)

    def idle(t):
        s = math.sin(2 * math.pi * t)
        p = {}
        p['spine'] = (-0.02 * s + hunch * 0.5, 0, 0)
        p['chest'] = (-0.025 * s + hunch * 0.5, 0, 0)
        p['neck'] = (0.02 * s - hunch * 0.6, 0.1 * math.sin(2 * math.pi * t + 1.0), 0)
        p['head'] = (-hunch * 0.3, 0.12 * math.sin(2 * math.pi * t * 1.0 + 0.4), 0.03 * s)
        arms_base(p, 0.03 * s)
        p['thigh.L'] = (0, 0, 0.02 * s)
        p['thigh.R'] = (0, 0, 0.02 * s)
        if elder:
            p['thigh.L'] = (-0.12, 0, 0)
            p['thigh.R'] = (-0.12, 0, 0)
            p['shin.L'] = (0.22, 0, 0)
            p['shin.R'] = (0.22, 0, 0)
            p['foot.L'] = (-0.1, 0, 0)
            p['foot.R'] = (-0.1, 0, 0)
        p['_loc'] = (0.01 * ch.H * s, -0.004 * ch.H * (1 - math.cos(2 * math.pi * t)) - (0.02 * ch.H if elder else 0), 0)
        extras(p, t, 1.0)
        return p

    def walk(t, run=False):
        s = math.sin(2 * math.pi * t)
        c = math.cos(2 * math.pi * t)
        A = 0.75 if run else 0.42
        K = 1.35 if run else 0.7
        p = {}
        lean = -0.22 if run else 0.0
        p['spine'] = (lean * 0.5 + hunch * 0.5, 0.06 * s, 0)
        p['chest'] = (lean * 0.5 + hunch * 0.4, -0.1 * s, 0)
        p['neck'] = (-lean * 0.6 - hunch * 0.6, 0.04 * s, 0)
        p['head'] = (-lean * 0.3, 0, 0)
        p['thigh.L'] = (-A * s, 0, 0)
        p['thigh.R'] = (A * s, 0, 0)
        p['shin.L'] = (0.08 + K * max(0.0, c) * (0.6 + 0.4 * max(0, s)), 0, 0)
        p['shin.R'] = (0.08 + K * max(0.0, -c) * (0.6 + 0.4 * max(0, -s)), 0, 0)
        p['foot.L'] = (-0.2 * s - 0.25 * max(0, c), 0, 0)
        p['foot.R'] = (0.2 * s - 0.25 * max(0, -c), 0, 0)
        B = 0.6 if run else 0.32
        arms_base(p, B * s, -1.2 if run else -0.3)
        if run:
            p['upper_arm.L'] = (B * s, 0, arm_down - 0.15)
            p['upper_arm.R'] = (-B * s, 0, -arm_down + 0.15)
            if held_r and held_r != 'lantern':
                p['upper_arm.R'] = (-0.4, 0, -arm_down + 0.15)
                p['forearm.R'] = (-1.3, 0, 0)
        bob = (0.045 if run else 0.022) * ch.H
        p['_loc'] = (0, -bob * (0.5 - 0.5 * math.cos(4 * math.pi * t)) - (0.04 * ch.H if run else 0), 0)
        extras(p, t, 1.6 if run else 1.0, 2.0)
        return p

    def sit(t):
        s = math.sin(2 * math.pi * t)
        p = {}
        p['spine'] = (-0.05 * s * 0.4 + 0.05 + hunch * 0.6, 0, 0)
        p['chest'] = (-0.02 * s + hunch * 0.4, 0, 0)
        p['neck'] = (-0.05 - hunch * 0.5, 0.1 * math.sin(2 * math.pi * t), 0)
        p['head'] = (0, 0.08 * math.sin(2 * math.pi * t + 0.5), 0)
        p['thigh.L'] = (-1.48, 0, -0.08)
        p['thigh.R'] = (-1.48, 0, 0.08)
        p['shin.L'] = (1.5, 0, 0)
        p['shin.R'] = (1.5, 0, 0)
        p['foot.L'] = (0.0, 0, 0)
        p['foot.R'] = (0.0, 0, 0)
        p['upper_arm.L'] = (-0.45, 0, arm_down)
        p['upper_arm.R'] = (-0.45, 0, -arm_down)
        p['forearm.L'] = (-0.85, 0, 0)
        p['forearm.R'] = (-0.85, 0, 0)
        p['_loc'] = (0, -ch.thigh_len * 0.97, -ch.thigh_len * 0.05)
        extras(p, t, 0.6)
        if tail:
            p[tail[0]] = (-0.9, 0, 0.2 * s)
        return p

    def talk(t):
        s = math.sin(2 * math.pi * t)
        g = math.sin(2 * math.pi * t * 2)
        p = idle(t)
        p['head'] = (0.08 * math.sin(2 * math.pi * t * 3), 0.15 * s, 0.05 * g)
        p['upper_arm.R'] = (-0.35 - 0.15 * g, 0, -arm_down + 0.15)
        p['forearm.R'] = (-1.1 - 0.25 * math.sin(2 * math.pi * t * 2 + 1), 0.3 * s, 0)
        p['hand.R'] = (0.2 * g, 0.4, 0)
        if not held_l or held_l == 'lantern':
            p['upper_arm.L'] = (-0.15 - 0.2 * max(0, math.sin(2 * math.pi * t + 2)), 0, arm_down - 0.1)
            p['forearm.L'] = (-0.6 - 0.4 * max(0, math.sin(2 * math.pi * t + 2)), 0, 0)
        p['chest'] = (0.0, 0.08 * s, 0)
        extras(p, t, 1.4, 1.5)
        return p

    def attack(t):
        p = idle(0.0)
        # windup 0-0.35, strike 0.35-0.55, recover 0.55-1
        def ease(a, b, u):
            u = clamp(u)
            u = u * u * (3 - 2 * u)
            return a + (b - a) * u
        if t < 0.35:
            u = t / 0.35
            ua_x, fa_x, sp_x, ch_y = ease(-0.25, -2.5, u), ease(-1.15, -1.3, u), ease(0, 0.12, u), ease(0, -0.35, u)
        elif t < 0.55:
            u = (t - 0.35) / 0.2
            ua_x, fa_x, sp_x, ch_y = ease(-2.5, -0.55, u), ease(-1.3, -0.25, u), ease(0.12, -0.25, u), ease(-0.35, 0.3, u)
        else:
            u = (t - 0.55) / 0.45
            ua_x, fa_x, sp_x, ch_y = ease(-0.55, -0.25, u), ease(-0.25, -1.15, u), ease(-0.25, 0, u), ease(0.3, 0, u)
        p['upper_arm.R'] = (ua_x, 0, -arm_down + 0.25)
        p['forearm.R'] = (fa_x, 0, 0)
        p['spine'] = (sp_x, ch_y * 0.5, 0)
        p['chest'] = (sp_x * 0.5, ch_y, 0)
        p['thigh.L'] = (-0.35, 0, 0.05)
        p['thigh.R'] = (0.25, 0, -0.05)
        p['shin.L'] = (0.35, 0, 0)
        p['shin.R'] = (0.2, 0, 0)
        p['_loc'] = (0, -0.035 * ch.H, 0)
        extras(p, t, 1.5, 2.0)
        return p

    return {
        'Idle': (idle, 2.4, 12, True),
        'Walk': (lambda t: walk(t), 1.1, 12, True),
        'Run': (lambda t: walk(t, True), 0.7, 12, True),
        'Sit': (sit, 3.0, 8, True),
        'Talk': (talk, 3.0, 18, True),
        'Attack': (attack, 1.1, 22, False),
    }


# ================================================================================================ blender assembly
MATS = {}


def materials():
    for name, emis in (('CharBody', 0.0), ('CharGlow', 2.5)):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
        nt.links.new(ca.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.9
        if emis:
            nt.links.new(ca.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = emis
        MATS[name] = m


def mesh_object(name, cm, coll):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in cm.v], [], cm.f)
    used = [m for m in ('CharBody', 'CharGlow') if m in set(cm.fm)]
    for mm in used:
        me.materials.append(MATS[mm])
    mi = {m: i for i, m in enumerate(used)}
    me.polygons.foreach_set('material_index', [mi[m] for m in cm.fm])
    col = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    lc = [0.0] * (len(me.loops) * 4)
    for p in me.polygons:
        c = cm.fc[p.index]
        for li in p.loop_indices:
            lc[li * 4:li * 4 + 4] = (c[0], c[1], c[2], 1.0)
    col.data.foreach_set('color_srgb', lc)
    me.color_attributes.active_color = col
    me.shade_flat()
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def build_character(ch, coll, offset):
    m = CMesh()
    BUILDERS[ch.sp](ch, m)
    # armature
    arm = bpy.data.armatures.new(ch.id + '_rig')
    ao = bpy.data.objects.new(ch.id, arm)
    coll.objects.link(ao)
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for name, (h, t) in ch.J.items():
        b = arm.edit_bones.new(name)
        b.head, b.tail = h, t
        x, z = bone_axes(t - h)
        b.align_roll(z)
        eb[name] = b
    for name, par in ch.parents.items():
        eb[name].parent = eb[par]
        eb[name].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    # skinned body
    mo = mesh_object(ch.id + '_body', m, coll)
    groups = {}
    for i, ws in enumerate(m.w):
        tot = sum(w for _, w in ws)
        for b, w in ws:
            if b not in ch.J:
                b = 'hips'
            groups.setdefault(b, []).append((i, w / tot))
    for b, items in groups.items():
        vg = mo.vertex_groups.new(name=b)
        for i, w in items:
            vg.add([i], w, 'ADD')
    mo.parent = ao
    mod = mo.modifiers.new('Armature', 'ARMATURE')
    mod.object = ao
    # held props, bone-parented
    held = PROPS[ch.sp][ch.idx % len(PROPS[ch.sp])]
    for s, kind in zip('RL', held):
        if not kind:
            continue
        pm = prop_mesh(kind, ch, s)
        po = mesh_object(f'{ch.id}_{kind}', pm, coll)
        po.parent = ao
        po.parent_type = 'BONE'
        po.parent_bone = f'hand.{s}'
        bone = arm.bones[f'hand.{s}']
        # keep the rest-pose world placement: bone-parent space is at the bone tail
        mw = ao.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
        po.matrix_parent_inverse = mw.inverted()
        ch.props.append(kind)
    # animations -> NLA tracks (one glTF animation each)
    ao.animation_data_create()
    for name, (fn, secs, keys, loop) in pose_fns(ch, held[0], held[1]).items():
        act = bpy.data.actions.new(f'{ch.id}_{name}')
        ao.animation_data.action = act
        frames = secs * FPS
        for i in range(keys + 1):
            t = i / keys
            pose = fn(t % 1.0 if loop else t)
            f = 1 + t * frames
            for pb in ao.pose.bones:
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = pose.get(pb.name, (0.0, 0.0, 0.0))
                pb.keyframe_insert('rotation_euler', frame=f)
            hip = ao.pose.bones['hips']
            lx, ly, lz = pose.get('_loc', (0, 0, 0))
            hip.location = (-lx, ly, lz)
            hip.keyframe_insert('location', frame=f)
        tr = ao.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 1, act)
        ao.animation_data.action = None
    for pb in ao.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    tris = sum(len(f) - 2 for f in m.f)
    return ao, tris


def main():
    import time
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials()
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith('.glb') or f.endswith('.glb.import'):
            os.remove(os.path.join(OUT_DIR, f))
    scn = bpy.context.scene
    manifest = []
    order = ['human', 'avari', 'keth', 'luma', 'vorn', 'murrai']
    for si, sp in enumerate(order):
        coll = bpy.data.collections.new(sp.capitalize())
        scn.collection.children.link(coll)
        for i in range(len(PROPS[sp])):
            ch = Char(sp, i, 1000 * si + i * 17 + 3)
            ao, tris = build_character(ch, coll, None)
            # export this character alone, at the origin
            bpy.ops.object.select_all(action='DESELECT')
            ao.select_set(True)
            for c in ao.children:
                c.select_set(True)
            bpy.context.view_layer.objects.active = ao
            path = os.path.join(OUT_DIR, ch.id + '.glb')
            bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                                      export_animation_mode='NLA_TRACKS', export_vertex_color='ACTIVE',
                                      export_all_vertex_colors=False, export_normals=True, export_texcoords=False,
                                      export_skins=True, export_yup=True, export_cameras=False, export_lights=False,
                                      export_optimize_animation_size=True)
            # then line it up in the .blend
            ao.location = (si * 3.0, i * 1.4, 0)
            manifest.append(dict(id=ch.id, species=sp, name=ch.name, age=ch.age, build=ch.build,
                                 height=round(ch.H, 3), props=ch.props, tris=tris, info=SPECIES_INFO[sp]))
            print(f'{ch.id:10s} {ch.name:12s} {ch.age:6s} {ch.build:8s} H={ch.H:.2f} tris={tris} props={ch.props}')
    with open(os.path.join(OUT_DIR, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1)
    w = bpy.data.worlds.new('Studio'); scn.world = w
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print(f'{len(manifest)} characters in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
