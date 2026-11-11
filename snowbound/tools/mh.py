"""Reads MakeHuman CC0 data (base mesh, shape targets, .mhclo proxies, skins) with our own code - no MakeHuman or MPFB
code is run. Every character in the game is built from this one base mesh, so they all share a body, a UV layout
and a skeleton.

Data is passed in as a directory (MH_DATA: the mpfb data folder with 3dobjs/ targets/ rigs/; MH_ASSETS: the
makehuman_system_assets_cc0 folder with skins/ eyes/ eyebrows/ hair/ clothes/).
"""
import gzip
import os

SCALE = 0.1  # MakeHuman units are decimetres


def load_obj(path, groups=None):
    """Returns (verts, uvs, faces, face_uvs, face_groups). Faces keep their original vertex indices."""
    verts, uvs, faces, fuvs, fgroups = [], [], [], [], []
    group = None
    with open(path) as f:
        for line in f:
            if line.startswith('v '):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('vt '):
                uvs.append([float(x) for x in line.split()[1:3]])
            elif line.startswith('g '):
                group = line.split()[1]
            elif line.startswith('f '):
                if groups is not None and group not in groups:
                    continue
                vi, ti = [], []
                for tok in line.split()[1:]:
                    parts = tok.split('/')
                    vi.append(int(parts[0]) - 1)
                    ti.append(int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1)
                faces.append(vi)
                fuvs.append(ti)
                fgroups.append(group)
    return verts, uvs, faces, fuvs, fgroups


def read_target(path):
    op = gzip.open if path.endswith('.gz') else open
    out = []
    with op(path, 'rt') as f:
        for line in f:
            if not line.strip() or line[0] == '#':
                continue
            p = line.split()
            out.append((int(p[0]), float(p[1]), float(p[2]), float(p[3])))
    return out


def apply_target(verts, path, weight):
    if weight == 0:
        return
    for i, dx, dy, dz in read_target(path):
        v = verts[i]
        v[0] += dx * weight
        v[1] += dy * weight
        v[2] += dz * weight


def macro(verts, data, gender, age, race, muscle=0.5, weight=0.5):
    """MakeHuman macro shape. gender 0 = female .. 1 = male; age in years (1..90); race = dict african/asian/caucasian
    -> share; muscle and weight 0..1 (0.5 = average)."""
    md = os.path.join(data, 'targets', 'macrodetails')
    ages = [('baby', 1), ('child', 11), ('young', 25), ('old', 90)]
    aw = {}
    for (a0, y0), (a1, y1) in zip(ages, ages[1:]):
        if y0 <= age <= y1:
            t = (age - y0) / (y1 - y0)
            aw = {a0: 1 - t, a1: t}
    gw = {'female': 1 - gender, 'male': gender}
    mw = {'minmuscle': max(0, 1 - muscle * 2), 'averagemuscle': 1 - abs(muscle - 0.5) * 2, 'maxmuscle': max(0, muscle * 2 - 1)}
    ww = {'minweight': max(0, 1 - weight * 2), 'averageweight': 1 - abs(weight - 0.5) * 2, 'maxweight': max(0, weight * 2 - 1)}
    for g, gv in gw.items():
        for a, av in aw.items():
            for mu, mv in mw.items():
                for we, wv in ww.items():
                    w = gv * av * mv * wv
                    if w > 1e-4:
                        apply_target(verts, os.path.join(md, f'universal-{g}-{a}-{mu}-{we}.target.gz'), w)
            for r, rv in race.items():
                w = gv * av * rv
                if w > 1e-4:
                    apply_target(verts, os.path.join(md, f'{r}-{g}-{a}.target.gz'), w)


def target(verts, data, rel, weight):
    """Apply one detail target by relative path under targets/, e.g. 'nose/nose-scale-horiz-incr'."""
    apply_target(verts, os.path.join(data, 'targets', rel + '.target.gz'), weight)


def fit_mhclo(body_verts, mhclo_path, deleted_out=None):
    """Fits a proxy (clothes, hair, eyes, eyebrows) to the shaped body. Returns (verts, obj_path, material_path).
    Body vertices the proxy hides (its delete_verts) are added to `deleted_out` if given."""
    base = os.path.dirname(mhclo_path)
    scales = {}
    refs = []
    obj_file = material = None
    deleted = set()
    section = None  # 'verts' once the vertex references start; keyword lines may still appear among them
    with open(mhclo_path) as f:
        for line in f:
            p = line.split()
            if not p or p[0].startswith('#'):
                continue
            if section == 'delete_verts' and p[0].isdigit():
                toks = line.replace(' - ', '-').split()
                for t in toks:
                    if '-' in t:
                        lo, hi = t.split('-')
                        deleted.update(range(int(lo), int(hi) + 1))
                    elif t.isdigit():
                        deleted.add(int(t))
                continue
            if p[0].lstrip('-').isdigit():
                if section == 'verts':
                    if len(p) == 9:
                        refs.append(([int(p[0]), int(p[1]), int(p[2])], [float(p[3]), float(p[4]), float(p[5])], [float(p[6]), float(p[7]), float(p[8])]))
                    elif len(p) == 1:
                        refs.append(([int(p[0])], [1.0], [0, 0, 0]))
                continue
            if p[0] in ('delete_verts', 'weights', 'offsets'):
                section = p[0]
            if p[0] in ('x_scale', 'y_scale', 'z_scale'):
                scales[p[0][0]] = (int(p[1]), int(p[2]), float(p[3]))
            elif p[0] == 'obj_file':
                obj_file = os.path.join(base, p[1])
            elif p[0] == 'material':
                material = os.path.join(base, p[1])
            elif p[0] == 'verts':
                section = 'verts'
    s = []
    for k, axis in (('x', 0), ('y', 1), ('z', 2)):
        if k in scales:
            a, b, d = scales[k]
            s.append(abs(body_verts[a][axis] - body_verts[b][axis]) / d)
        else:
            s.append(1.0)
    out = []
    for idx, w, off in refs:
        x = y = z = 0.0
        for i, wi in zip(idx, w):
            x += body_verts[i][0] * wi
            y += body_verts[i][1] * wi
            z += body_verts[i][2] * wi
        out.append([x + off[0] * s[0], y + off[1] * s[1], z + off[2] * s[2]])
    if deleted_out is not None:
        deleted_out.update(deleted)
    return out, obj_file, material


def read_mhmat(path):
    """Returns {key: value} for a .mhmat (diffuseTexture, normalmapTexture, diffuseColor...), with texture paths
    resolved next to the .mhmat."""
    out = {}
    base = os.path.dirname(path)
    with open(path) as f:
        for line in f:
            p = line.strip().split(None, 1)
            if len(p) == 2 and not p[0].startswith('#'):
                v = p[1]
                if p[0].endswith('Texture'):
                    v = os.path.join(base, os.path.basename(v))
                out[p[0]] = v
    return out
