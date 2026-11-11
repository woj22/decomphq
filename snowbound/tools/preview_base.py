"""Renders a preview of character base option B (MakeHuman CC0 data, read by tools/mh.py) for the user to approve.

    python3 snowbound/tools/preview_base.py MH_DATA MH_ASSETS OUT_DIR
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,I001
import bmesh  # noqa: E402
import blib  # noqa: E402
import mh  # noqa: E402

DATA, ASSETS, OUT = sys.argv[1:4]


def lin_img(path, alpha=False):
    img = bpy.data.images.load(path, check_existing=True)
    return img


def material(name, tex=None, rough=0.55, sss=0.0, alpha=False, normal=None):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Roughness'].default_value = rough
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.9, 0.35, 0.2)
        b.inputs['Subsurface Scale'].default_value = 0.01
    if tex:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = lin_img(tex)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        if alpha:
            nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
            try:
                m.blend_method = 'HASHED'
            except Exception:
                pass
    if normal and os.path.exists(normal):
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = lin_img(normal)
        t.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def mesh_obj(name, verts, faces, fuvs, uvs, mat, smooth=True):
    bm = bmesh.new()
    used = sorted({i for f in faces for i in f})
    remap = {}
    for i in used:
        x, y, z = verts[i]
        remap[i] = bm.verts.new(blib.g(x * mh.SCALE, y * mh.SCALE, z * mh.SCALE))
    uvl = bm.loops.layers.uv.new('UVMap')
    for f, fu in zip(faces, fuvs):
        try:
            face = bm.faces.new([remap[i] for i in f])
        except ValueError:
            continue
        face.smooth = smooth
        for loop, ti in zip(face.loops, fu):
            if ti >= 0:
                loop[uvl].uv = uvs[ti]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    return o


def proxy(body, rel, mat_override=None, sss=0.0, alpha=False, rough=0.6, hidden=None):
    path = os.path.join(ASSETS, rel)
    pv, objp, matp = mh.fit_mhclo(body, path, hidden)
    _, uvs, faces, fuvs, _ = mh.load_obj(objp)
    mm = mh.read_mhmat(mat_override or matp)
    m = material(os.path.basename(rel), mm.get('diffuseTexture'), rough=rough, sss=sss, alpha=alpha, normal=mm.get('normalmapTexture'))
    return mesh_obj(os.path.basename(rel), pv, faces, fuvs, uvs, m)


def person(x_offset, gender, age, race, skin, hair, clothes, eyes='brown', extra=()):
    verts, uvs, faces, fuvs, groups = mh.load_obj(os.path.join(DATA, '3dobjs', 'base.obj'), groups={'body'})
    mh.macro(verts, DATA, gender, age, race)
    for rel, w in extra:
        mh.target(verts, DATA, rel, w)
    sk = mh.read_mhmat(os.path.join(ASSETS, 'skins', skin, skin + '.mhmat'))
    hidden = set()
    objs = [proxy(verts, 'eyes/high-poly/high-poly.mhclo', os.path.join(ASSETS, 'eyes/materials', eyes + '.mhmat'), rough=0.1, alpha=True)]
    objs.append(proxy(verts, 'eyebrows/eyebrow001/eyebrow001.mhclo', alpha=True))
    objs.append(proxy(verts, 'eyelashes/eyelashes01/eyelashes01.mhclo', alpha=True) if os.path.exists(os.path.join(ASSETS, 'eyelashes/eyelashes01/eyelashes01.mhclo')) else None)
    objs.append(proxy(verts, f'hair/{hair}/{hair}.mhclo', alpha=True, rough=0.45))
    for c in clothes:
        objs.append(proxy(verts, f'clothes/{c}/{c}.mhclo', rough=0.8, hidden=hidden))
    keep = [(f, fu) for f, fu in zip(faces, fuvs) if not any(i in hidden for i in f)]
    objs.append(mesh_obj('body', verts, [k[0] for k in keep], [k[1] for k in keep], uvs, material('skin', sk.get('diffuseTexture'), rough=0.5, sss=0.12)))
    for o in objs:
        if o:
            o.location.x += x_offset
    top = max(v[1] for v in verts) * mh.SCALE
    return top


blib.reset()
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 48
sc.render.resolution_x, sc.render.resolution_y = 1100, 900
try:
    sc.cycles.use_denoising = True
except Exception:
    pass
sc.view_settings.view_transform = 'AgX'
blib.world_sky((0.05, 0.04, 0.04), 0.4)
top = person(-0.32, 1.0, 70, {'asian': 1.0}, 'old_asian_male', 'short02', ['male_casualsuit04'])
person(0.32, 0.0, 34, {'caucasian': 1.0}, 'young_caucasian_female', 'ponytail01', ['female_elegantsuit01'], eyes='bluegreen')
blib.point_light('key', (-1.2, top + 0.2, 1.4), (1.0, 0.78, 0.55), 160, 0.3)
blib.point_light('fill', (1.4, top - 0.2, 1.0), (0.55, 0.65, 1.0), 60, 0.5)
blib.point_light('rim', (0.0, top + 0.5, -1.2), (1.0, 0.85, 0.7), 90, 0.3)
cam_d = bpy.data.cameras.new('cam')
cam_d.lens = 70
cam = bpy.data.objects.new('cam', cam_d)
sc.collection.objects.link(cam)
sc.camera = cam


def shoot(name, target, dist, lens):
    cam_d.lens = lens
    cam.location = blib.g(target[0], target[1], target[2] + dist)
    d = blib.g(*target) - cam.location
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


os.makedirs(OUT, exist_ok=True)
shoot('B_busts', (0.0, top - 0.2, 0.0), 2.2, 70)
shoot('B_full', (0.0, top / 2, 0.0), 5.2, 50)
