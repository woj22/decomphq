import bpy, bmesh, math, time, os, sys
from mathutils import Vector
PPU = 64/math.sqrt(2)   # px per world unit along screen-x  (tile 1u -> 64x32 diamond)
ZPX = PPU*math.cos(math.radians(30))  # px per unit of height (39.19)

def reset(samples=16, filt=0.01):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = samples
    s.cycles.use_adaptive_sampling = False
    s.cycles.use_denoising = False
    s.cycles.pixel_filter_type = 'BOX'
    s.cycles.filter_width = filt
    s.cycles.max_bounces = 2
    s.render.film_transparent = True
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    s.render.resolution_percentage = 100
    s.view_settings.view_transform = 'Standard'
    s.view_settings.look = 'None'
    s.render.use_persistent_data = True
    s.render.threads_mode = 'FIXED'; s.render.threads = 4
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.42, 0.36, 0.62, 1)   # cold purple ambient
    bg.inputs[1].default_value = 0.55
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'
    co = bpy.data.objects.new('cam', cam); s.collection.objects.link(co); s.camera = co
    co.rotation_euler = (math.radians(60), 0, math.radians(45))
    return s

def aim(s, w, h, target=(0,0,0)):
    """canvas w x h px; world point `target` lands on canvas centre."""
    s.render.resolution_x = w; s.render.resolution_y = h
    cam = s.camera
    cam.data.ortho_scale = max(w, h)/PPU
    d = 30
    dirv = Vector((math.sin(math.radians(60))*math.sin(math.radians(45)),
                   -math.sin(math.radians(60))*math.cos(math.radians(45)),
                   math.cos(math.radians(60))))
    cam.location = Vector(target) + dirv*d
    cam.data.clip_end = 200

def sun(s, rot, color, strength, angle=0.02):
    l = bpy.data.lights.new('sun', 'SUN'); l.energy = strength; l.color = color; l.angle = angle
    o = bpy.data.objects.new('sun', l); s.collection.objects.link(o)
    o.rotation_euler = [math.radians(a) for a in rot]; return o

def point(s, loc, color, watts, r=0.05):
    l = bpy.data.lights.new('pt', 'POINT'); l.energy = watts; l.color = color; l.shadow_soft_size = r
    o = bpy.data.objects.new('pt', l); s.collection.objects.link(o); o.location = loc; return o

def mat_flat(name, rgb, emit=0.0, ecol=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = 1
    b.inputs['Specular IOR Level'].default_value = 0
    if emit:
        b.inputs['Emission Color'].default_value = (*(ecol or rgb), 1)
        b.inputs['Emission Strength'].default_value = emit
    return m

def mat_stone(name, c1, c2, mortar, wall=False, bw=0.5, bh=0.25, mort=0.02):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 1; b.inputs['Specular IOR Level'].default_value = 0
    tc = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Position'], sep.inputs[0])
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    if wall:
        add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
        nt.links.new(sep.outputs[0], add.inputs[0]); nt.links.new(sep.outputs[1], add.inputs[1])
        nt.links.new(add.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[2], comb.inputs[1])
    else:
        nt.links.new(sep.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[1], comb.inputs[1])
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = (*c1, 1); br.inputs['Color2'].default_value = (*c2, 1)
    br.inputs['Mortar'].default_value = (*mortar, 1)
    br.inputs['Scale'].default_value = 1
    br.inputs['Mortar Size'].default_value = mort
    br.inputs['Mortar Smooth'].default_value = 0
    br.inputs['Bias'].default_value = 0
    br.inputs['Brick Width'].default_value = bw; br.inputs['Row Height'].default_value = bh
    nt.links.new(comb.outputs[0], br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    return m

def box(s, name, lo, hi, mat):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); s.collection.objects.link(o)
    lo, hi = Vector(lo), Vector(hi)
    o.scale = hi-lo; o.location = (lo+hi)/2
    me.materials.append(mat); return o

def cone(s, name, r1, r2, z0, z1, mat, seg=10, loc=(0,0), smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=z1-z0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = len(p.vertices) == 4
    o = bpy.data.objects.new(name, me); s.collection.objects.link(o)
    o.location = (loc[0], loc[1], (z0+z1)/2); me.materials.append(mat); return o

def sphere(s, name, r, loc, mat, scale=(1,1,1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); s.collection.objects.link(o)
    o.location = loc; o.scale = scale; me.materials.append(mat); return o

def arch_prism(s, name, half_w, spring, depth, mat=None, n=8):
    """pointed (equilateral) gothic arch profile in XZ, extruded along Y (centred)."""
    pts = [(-half_w, 0), (half_w, 0), (half_w, spring)]
    R = 2*half_w
    for i in range(1, n+1):       # right arc, centre at (-half_w, spring)
        a = math.radians(60*i/n); pts.append((-half_w + R*math.cos(a), spring + R*math.sin(a)))
    for i in range(n-1, -1, -1):  # left arc, centre at (half_w, spring)
        a = math.radians(60*i/n); pts.append((half_w - R*math.cos(a), spring + R*math.sin(a)))
    bm = bmesh.new()
    vs = [bm.verts.new((x, -depth/2, z)) for x, z in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); s.collection.objects.link(o)
    if mat: me.materials.append(mat)
    return o

def render(s, path):
    t = time.time(); s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return time.time()-t
