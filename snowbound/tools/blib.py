"""Small bpy toolkit for the Last Carriage models.

Everything is authored in GODOT coordinates (x right, y up, z toward the viewer) through g(); the glTF
exporter's +Y-up conversion maps Blender (x, y, z) -> Godot (x, z, -y), so g(x, y, z) = Blender (x, -z, y).
Objects are built from bmesh primitives (no bpy.ops), modifiers are evaluated on merge, and every
exported node is one merged mesh with several material slots, so a whole character is a handful of draw calls.
"""
import math
import bpy  # noqa: I001 (bpy must load before bmesh/mathutils)
import bmesh
from mathutils import Matrix, Vector

TAU = math.tau


def g(x, y, z):
    return Vector((x, -z, y))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()


# ------------------------------------------------------------------ materials
MATS = {}


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def mat(name, hexcol='#888888', rough=0.7, metal=0.0, emit=None, strength=1.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = m.node_tree.nodes.get('Principled BSDF')
    h = hexcol.lstrip('#')
    rgb = [_lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)]
    b.inputs['Base Color'].default_value = (*rgb, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        e = emit.lstrip('#')
        b.inputs['Emission Color'].default_value = (*[_lin(int(e[i:i + 2], 16)) for i in (0, 2, 4)], 1.0)
        b.inputs['Emission Strength'].default_value = strength
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
    MATS[name] = m
    return m


# ------------------------------------------------------------------ objects
def _obj(name, bm, material, smooth=False, sharp_angle=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    for f in bm.faces:
        f.smooth = smooth
    if smooth and sharp_angle is not None:
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(sharp_angle):
                e.smooth = False
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    if material is not None:
        me.materials.append(material)
    return o


def place(o, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """loc/rot/scale in Godot axes. rot = Euler XYZ degrees about Godot axes."""
    o.location = g(*loc)
    rx, ry, rz = (math.radians(a) for a in rot)
    # Godot X -> Blender X, Godot Y -> Blender Z, Godot Z -> Blender -Y
    o.rotation_mode = 'XYZ'
    m = Matrix.Rotation(rz, 4, Vector((0, -1, 0))) @ Matrix.Rotation(ry, 4, Vector((0, 0, 1))) @ Matrix.Rotation(rx, 4, Vector((1, 0, 0)))
    o.rotation_euler = m.to_euler('XYZ')
    o.scale = (scale[0], scale[2], scale[1])
    return o


def box(name, size, loc, material, bevel=0.0, seg=2, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[2], v.co.z * size[1]))
    o = _obj(name, bm, material, smooth=bevel > 0, sharp_angle=50)
    if bevel > 0:
        b = o.modifiers.new('bevel', 'BEVEL')
        b.width = bevel
        b.segments = seg
        b.limit_method = 'ANGLE'
    return place(o, loc, rot)


def cyl(name, r1, r2, depth, loc, material, segs=24, rot=(0, 0, 0), cap=True, smooth=True):
    """Cylinder/cone along Godot Y. r1 = bottom radius, r2 = top."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    return place(_obj(name, bm, material, smooth=smooth, sharp_angle=45), loc, rot)


def sphere(name, r, loc, material, scale=(1, 1, 1), rot=(0, 0, 0), segs=24, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    return place(_obj(name, bm, material, smooth=True), loc, rot, scale)


def torus(name, R, r, loc, material, segs=32, rsegs=10, rot=(0, 0, 0), arc=TAU, scale=(1, 1, 1)):
    """Torus lying flat (ring in the Godot XZ plane)."""
    bm = bmesh.new()
    rings = []
    closed = abs(arc - TAU) < 1e-6
    n = segs if closed else segs + 1
    for i in range(n):
        a = arc * i / segs
        ring = []
        for j in range(rsegs):
            b = TAU * j / rsegs
            x = (R + r * math.cos(b)) * math.cos(a)
            zz = (R + r * math.cos(b)) * math.sin(a)
            y = r * math.sin(b)
            ring.append(bm.verts.new(g(x, y, zz)))
        rings.append(ring)
    for i in range(n if closed else n - 1):
        a, b2 = rings[i], rings[(i + 1) % n]
        for j in range(rsegs):
            bm.faces.new((a[j], a[(j + 1) % rsegs], b2[(j + 1) % rsegs], b2[j]))
    return place(_obj(name, bm, material, smooth=True), loc, rot, scale)


def tube(name, pts, radii, material, segs=12, cap=True):
    """Swept tube along a polyline of Godot points with per-point radius (limbs, rails, scarves)."""
    bm = bmesh.new()
    rings = []
    P = [g(*p) for p in pts]
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        side = d.cross(up).normalized()
        up2 = side.cross(d).normalized()
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        rings.append([bm.verts.new(p + (side * math.cos(TAU * j / segs) + up2 * math.sin(TAU * j / segs)) * r) for j in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj(name, bm, material, smooth=True)


def skin_body(name, verts, edges, radii, material, subsurf=2):
    """Skin modifier + subdivision: smooth organic shapes from a stick figure (Godot points)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([g(*v) for v in verts], edges, [])
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.modifiers.new('skin', 'SKIN')
    sv = me.skin_vertices[0].data
    for i, r in enumerate(radii):
        sv[i].radius = r if isinstance(r, (list, tuple)) else (r, r)
    sv[0].use_root = True
    s = o.modifiers.new('sub', 'SUBSURF')
    s.levels = s.render_levels = subsurf
    me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    return o


def subsurf(o, levels=2):
    s = o.modifiers.new('sub', 'SUBSURF')
    s.levels = s.render_levels = levels
    return o


def deform(o, fn):
    """Apply fn(godot_xyz) -> godot_xyz to every vertex (object space, before placement)."""
    for v in o.data.vertices:
        x, y, z = v.co.x, v.co.z, -v.co.y
        nx, ny, nz = fn(x, y, z)
        v.co = Vector((nx, -nz, ny))
    return o


def delete_verts(o, pred):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    kill = [v for v in bm.verts if pred(v.co.x, v.co.z, -v.co.y)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(o.data)
    bm.free()
    return o


def solidify(o, t):
    m = o.modifiers.new('solid', 'SOLIDIFY')
    m.thickness = t
    m.offset = 1.0
    return o


# ------------------------------------------------------------------ merge + export
def merge(objs, name, parent=None):
    """Evaluate modifiers and merge objects into one mesh (several material slots). If parent is given the
    result is parented to it with vertices expressed in the parent's space."""
    objs = [o for o in objs if o is not None]
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    inv = parent.matrix_world.inverted() if parent is not None else Matrix.Identity(4)
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        if not me.uv_layers:
            me.uv_layers.new(name='UVMap')  # every part has one, so merged UVs line up
        me.transform(inv @ o.matrix_world)
        if (inv @ o.matrix_world).determinant() < 0:
            me.flip_normals()
        remap = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        for p in me.polygons:
            p.material_index = remap[p.material_index] if remap else 0
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    for m in mats:
        out.materials.append(m)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    res = bpy.data.objects.new(name, out)
    bpy.context.scene.collection.objects.link(res)
    if parent is not None:
        res.parent = parent
    return res


def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = g(*loc)
    if parent is not None:
        e.parent = parent
        e.location = g(*loc) - parent.location
    bpy.context.view_layer.update()
    return e


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_extras=False)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
    print(f'exported {path}: {tris} tris, {sum(1 for o in bpy.data.objects if o.type == "MESH")} meshes')


# ================================================================== UVs, lightmap bake (Snowbound additions)
def box_uv(o, scales, default=1.0, keep=('Runner', 'Picture')):
    """World-scale box-projection UVs on the first UV layer: walls get (along, up), floors (x, z). `scales` maps a
    material name to metres per texture repeat, so wood grain and fabric patterns are the same size everywhere."""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers[0]
    for p in me.polygons:
        mname = me.materials[p.material_index].name if me.materials else ''
        if mname in keep:
            continue  # these parts carry their own UVs
        s = scales.get(mname, default)
        n = p.normal  # Blender axes: Godot x = bx, Godot y = bz, Godot z = -by
        ax, ay, az = abs(n.x), abs(n.z), abs(n.y)
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            gx, gy, gz = co.x, co.z, -co.y
            if ay >= ax and ay >= az:
                u, v = gx, gz
            elif ax >= az:
                u, v = gz, gy
            else:
                u, v = gx, gy
            uv.data[li].uv = (u / s, v / s)


def lightmap_uv(o, margin=0.012):
    me = o.data
    if 'lightmap' not in me.uv_layers:
        me.uv_layers.new(name='lightmap')
    me.uv_layers.active = me.uv_layers['lightmap']
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=1.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers.active = me.uv_layers[0]


def point_light(name, loc, colour, watts, radius=0.05):
    d = bpy.data.lights.new(name, 'POINT')
    d.energy = watts
    d.color = colour
    d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = g(*loc)
    return o


def area_light(name, loc, colour, watts, size, facing):
    """Rectangular area light at loc (Godot), shining along `facing` (a Godot direction)."""
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = watts
    d.color = colour
    d.shape = 'RECTANGLE'
    d.size, d.size_y = size
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = g(*loc)
    direction = g(*facing).normalized()
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = direction.to_track_quat('-Z', 'Y')
    return o


def world_sky(colour, strength):
    w = bpy.data.worlds.new('sky')
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (*colour, 1)
    bg.inputs['Strength'].default_value = strength


def bake_lightmap(o, res, path, samples=96, scale=2.0, blur=1.0):
    """Bake diffuse direct+indirect light (no albedo) into o's 'lightmap' UVs. Stored as sRGB PNG of light/scale,
    so 0..scale fits in 8 bits; the game multiplies it back by `scale`."""
    import numpy as np
    from PIL import Image, ImageFilter
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 3
    sc.render.bake.margin = 6
    img = bpy.data.images.new(o.name + '_lm', res, res, float_buffer=True)
    for m in o.data.materials:
        nt = m.node_tree
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        nt.nodes.active = n
    me = o.data
    me.uv_layers.active = me.uv_layers['lightmap']
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=6)
    me.uv_layers.active = me.uv_layers[0]
    px = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)[::-1, :, :3]
    enc = np.clip(px / scale, 0, 1) ** (1 / 2.2)
    im = Image.fromarray((enc * 255 + 0.5).astype(np.uint8))
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))  # bake noise
    im.save(path)
    for m in o.data.materials:  # the exported materials must not carry the bake image
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type == 'TEX_IMAGE' and n.image == img:
                nt.nodes.remove(n)
    print(f'baked {path} ({res}px, {samples} spp, peak {px.max():.2f})')


def export_objects(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True, export_yup=True,
                              use_selection=True, export_materials='EXPORT', export_texcoords=True,
                              export_extras=False, export_lights=False, export_cameras=False)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH')
    print(f'exported {path}: {tris} tris')
