"""bpy helpers: scene/camera/light setup and primitive builders (seeded from tools/experiments/art/lib.py).

Coordinates: Blender (X, Y) = Godot (cx, -cy). +X = screen SE, +Y = screen NE, 1 BU = one 64x32 tile.
The camera is orthographic, rotation (60°, 0°, 45°). A world point P projects to canvas pixel
    sx = ox + (P.x + P.y) * 32,   sy = oy + (P.x - P.y) * 16 - P.z * ZPX
where (ox, oy) is the sprite origin (the pixel that the world origin lands on).
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'procgen'))
from palette import lin  # noqa: E402

PPU = 64 / math.sqrt(2)                    # px per BU in the camera plane (45.2548)
ZPX = PPU * math.cos(math.radians(30))     # px per BU of height (39.19)
HU = 16 / ZPX                              # one height unit in BU
STOREY = 96 / ZPX
R_VEC = Vector((1, 1, 0)).normalized()                                  # camera right
U_VEC = Vector((-math.sin(math.radians(45)) * 0.5, math.cos(math.radians(45)) * 0.5, math.sin(math.radians(60))))  # camera up
D_VEC = Vector((math.sin(math.radians(60)) * math.sin(math.radians(45)),
                -math.sin(math.radians(60)) * math.cos(math.radians(45)), math.cos(math.radians(60))))  # toward camera

KEY_DIR = (0.45, 0.8, -1.3)
FILL_DIR = (-0.9, -0.2, -0.6)


def project(p, origin):
    ox, oy = origin
    return ox + (p[0] + p[1]) * 32, oy + (p[0] - p[1]) * 16 - p[2] * ZPX


class Ctx:
    """One Blender scene reused for many renders; `kit` collection is cleared between sprites."""

    def __init__(self, outdir, samples=64, threads=1, key=4.5, fill=0.6, world=0.55):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        s = self.s = bpy.context.scene
        s.render.engine = 'CYCLES'
        s.cycles.device = 'CPU'
        s.cycles.samples = samples
        s.cycles.seed = 7
        s.cycles.use_adaptive_sampling = False
        s.cycles.use_denoising = False
        s.cycles.pixel_filter_type = 'GAUSSIAN'
        s.cycles.filter_width = 0.01
        s.cycles.max_bounces = 2
        s.cycles.diffuse_bounces = 2
        s.cycles.glossy_bounces = 0
        s.cycles.transmission_bounces = 0
        s.cycles.transparent_max_bounces = 2
        s.render.film_transparent = True
        s.render.image_settings.file_format = 'PNG'
        s.render.image_settings.color_mode = 'RGBA'
        s.render.image_settings.color_depth = '8'
        s.render.resolution_percentage = 100
        s.view_settings.view_transform = 'Standard'
        s.view_settings.look = 'None'
        s.render.use_persistent_data = True
        s.render.threads_mode = 'FIXED'
        s.render.threads = threads
        w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
        bg = w.node_tree.nodes['Background']
        bg.inputs[0].default_value = (0.42, 0.36, 0.62, 1)
        bg.inputs[1].default_value = world
        cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.clip_start = 0.1; cam.clip_end = 200
        co = bpy.data.objects.new('cam', cam); s.collection.objects.link(co); s.camera = co
        co.rotation_euler = (math.radians(60), 0, math.radians(45))
        self.key = self.sun(KEY_DIR, (1.0, 0.95, 0.88), key)
        self.fill = self.sun(FILL_DIR, (0.55, 0.45, 0.9), fill)
        self.outdir = outdir
        self.mats = {}
        self.kit = None
        self.new_kit()

    # ---- scene management
    def sun(self, d, color, strength, angle=0.02):
        l = bpy.data.lights.new('sun', 'SUN'); l.energy = strength; l.color = color; l.angle = angle
        o = bpy.data.objects.new('sun', l); self.s.collection.objects.link(o)
        o.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler(); return o

    def point(self, loc, color, watts, r=0.05):
        l = bpy.data.lights.new('pt', 'POINT'); l.energy = watts; l.color = color; l.shadow_soft_size = r
        o = bpy.data.objects.new('pt', l); self.kit.objects.link(o); o.location = loc; return o

    def new_kit(self):
        if self.kit is not None:
            for o in list(self.kit.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            for m in list(bpy.data.meshes):
                if m.users == 0:
                    bpy.data.meshes.remove(m)
        else:
            self.kit = bpy.data.collections.new('kit'); self.s.collection.children.link(self.kit)

    def link(self, o):
        self.kit.objects.link(o); return o

    def empty(self, name='e', loc=(0, 0, 0), parent=None):
        o = bpy.data.objects.new(name, None); self.link(o); o.location = loc
        if parent: o.parent = parent
        return o

    def aim(self, w, h, origin):
        """canvas w x h px; world origin lands on pixel `origin` (boundary coords, e.g. (32,112))."""
        s = self.s
        s.render.resolution_x = w; s.render.resolution_y = h
        cam = s.camera
        cam.data.ortho_scale = max(w, h) / PPU
        ox, oy = origin
        target = R_VEC * ((w / 2 - ox) / PPU) - U_VEC * ((h / 2 - oy) / PPU)
        cam.location = target + D_VEC * 40

    def render(self, name, w, h, origin):
        self.aim(w, h, origin)
        self.s.render.filepath = os.path.join(self.outdir, name + '.png')
        bpy.ops.render.render(write_still=True)

    # ---- materials
    def m(self, hexcol, emit=0.0, ecol=None, rough=1.0):
        k = (hexcol, emit, ecol)
        if k in self.mats: return self.mats[k]
        mt = bpy.data.materials.new(f'{hexcol}_{emit}')
        mt.use_nodes = True
        b = mt.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*lin(hexcol), 1)
        b.inputs['Roughness'].default_value = rough
        b.inputs['Specular IOR Level'].default_value = 0
        if emit:
            b.inputs['Emission Color'].default_value = (*lin(ecol or hexcol), 1)
            b.inputs['Emission Strength'].default_value = emit
        self.mats[k] = mt
        return mt

    def brick(self, name, c1, c2, mortar, bw, bh, mort, wall=True, offset=(0, 0), squash=0.5):
        """Brick texture in world space. Walls: u = x+y (both orientations share it), v = z."""
        k = ('brick', name)
        if k in self.mats: return self.mats[k]
        mt = bpy.data.materials.new(name); mt.use_nodes = True
        nt = mt.node_tree; b = nt.nodes['Principled BSDF']
        b.inputs['Roughness'].default_value = 1; b.inputs['Specular IOR Level'].default_value = 0
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
        comb = nt.nodes.new('ShaderNodeCombineXYZ')
        if wall:
            add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
            nt.links.new(sep.outputs[0], add.inputs[0]); nt.links.new(sep.outputs[1], add.inputs[1])
            a2 = nt.nodes.new('ShaderNodeMath'); a2.operation = 'ADD'; a2.inputs[1].default_value = offset[0]
            nt.links.new(add.outputs[0], a2.inputs[0]); nt.links.new(a2.outputs[0], comb.inputs[0])
            a3 = nt.nodes.new('ShaderNodeMath'); a3.operation = 'ADD'; a3.inputs[1].default_value = offset[1]
            nt.links.new(sep.outputs[2], a3.inputs[0]); nt.links.new(a3.outputs[0], comb.inputs[1])
        else:
            nt.links.new(sep.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[1], comb.inputs[1])
        br = nt.nodes.new('ShaderNodeTexBrick')
        br.inputs['Color1'].default_value = (*lin(c1), 1); br.inputs['Color2'].default_value = (*lin(c2), 1)
        br.inputs['Mortar'].default_value = (*lin(mortar), 1)
        br.inputs['Scale'].default_value = 1
        br.inputs['Mortar Size'].default_value = mort
        br.inputs['Mortar Smooth'].default_value = 0
        br.inputs['Bias'].default_value = 0
        br.inputs['Brick Width'].default_value = bw; br.inputs['Row Height'].default_value = bh
        br.offset = 0.5; br.squash = 1.0
        nt.links.new(comb.outputs[0], br.inputs['Vector'])
        nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
        self.mats[k] = mt
        return mt

    # ---- primitives
    def _obj(self, name, me, mat, parent=None):
        o = bpy.data.objects.new(name, me); self.link(o)
        if mat: me.materials.append(mat)
        if parent: o.parent = parent
        return o

    def box(self, lo, hi, mat, parent=None, name='box'):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = self._obj(name, me, mat, parent)
        lo, hi = Vector(lo), Vector(hi)
        o.scale = hi - lo; o.location = (lo + hi) / 2
        return o

    def cyl(self, r1, r2, z0, z1, mat, seg=12, loc=(0, 0), scale=(1, 1), parent=None, smooth=True, name='cyl'):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=z1 - z0)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        if smooth:
            for p in me.polygons: p.use_smooth = len(p.vertices) == 4
        o = self._obj(name, me, mat, parent)
        o.location = (loc[0], loc[1], (z0 + z1) / 2); o.scale = (scale[0], scale[1], 1)
        return o

    def sphere(self, r, loc, mat, scale=(1, 1, 1), parent=None, seg=16, rings=10, name='sph'):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        for p in me.polygons: p.use_smooth = True
        o = self._obj(name, me, mat, parent)
        o.location = loc; o.scale = scale
        return o

    def poly_prism(self, pts, depth, mat, parent=None, name='prism'):
        """polygon in XZ (list of (x,z)), extruded along +Y from y=-depth/2 .. +depth/2."""
        bm = bmesh.new()
        vs = [bm.verts.new((x, -depth / 2, z)) for x, z in pts]
        f = bm.faces.new(vs)
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, depth, 0))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        return self._obj(name, me, mat, parent)

    def arch(self, half_w, spring, depth, mat=None, n=10, parent=None, name='arch'):
        """pointed (equilateral) gothic arch profile in XZ, extruded along Y (centred)."""
        return self.poly_prism(arch_pts(half_w, spring, n), depth, mat, parent, name)

    def mesh(self, verts, faces, mat, parent=None, name='mesh', smooth=False):
        me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
        if smooth:
            for p in me.polygons: p.use_smooth = True
        return self._obj(name, me, mat, parent)

    def cut(self, target, cutter):
        md = target.modifiers.new('b', 'BOOLEAN'); md.object = cutter; md.operation = 'DIFFERENCE'; md.solver = 'EXACT'
        cutter.hide_render = True
        return md


def arch_pts(half_w, spring, n=10):
    pts = [(-half_w, 0), (half_w, 0), (half_w, spring)]
    R = 2 * half_w
    for i in range(1, n + 1):
        a = math.radians(60 * i / n); pts.append((-half_w + R * math.cos(a), spring + R * math.sin(a)))
    for i in range(n - 1, -1, -1):
        a = math.radians(60 * i / n); pts.append((half_w - R * math.cos(a), spring + R * math.sin(a)))
    # drop duplicate apex / spring points
    out = []
    for p in pts:
        if not out or (abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6):
            out.append(p)
    if abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out
