"""The shared character base for Snowbound, built entirely by our own code: a standing body grown from a skeleton
(skin modifier + subdivision), a modelled head, fingered hands, our own skeleton, computed skin weights, and
keyframed actions (idle, walk, sit, sit_talk, talk). Every character is this base with different proportions,
colours and costume pieces.

Godot coordinates throughout (via blib.g): x = the character's left, y up, z forward (the character faces +z).
"""
import math

import bpy  # noqa: I001
import bmesh
from mathutils import Matrix, Quaternion, Vector

import blib
from blib import box, cyl, deform, delete_verts, g, mat, place, solidify, sphere, tube


def V(*a):
    return Vector(a)


class Person:
    def __init__(self, name, height=1.74, build=1.0, female=False, head_scale=1.0, belly=0.0, age=40):
        self.name = name
        k = height / 1.74
        self.k, self.build, self.female, self.age = k, build, female, age
        sw = (0.165 if female else 0.19) * k * (0.92 + 0.08 * build)
        hw = (0.115 if female else 0.095) * k * (0.9 + 0.1 * build)
        self.J = {
            'hips': V(0, 0.98 * k, 0), 'waist': V(0, 1.1 * k, -0.005), 'chest': V(0, 1.3 * k, 0.0),
            'neck': V(0, 1.47 * k, -0.01), 'head': V(0, 1.555 * k, 0.0), 'crown': V(0, 1.74 * k, 0.0),
        }
        for s, sx in (('L', 1), ('R', -1)):
            self.J['clav' + s] = V(sx * 0.035 * k, 1.44 * k, -0.01)
            self.J['shoulder' + s] = V(sx * sw, 1.43 * k, -0.02)
            self.J['elbow' + s] = V(sx * (sw + 0.085 * k), 1.165 * k, -0.04)
            self.J['wrist' + s] = V(sx * (sw + 0.15 * k), 0.92 * k, 0.0)
            self.J['fingers' + s] = V(sx * (sw + 0.175 * k), 0.8 * k, 0.015)
            self.J['hip' + s] = V(sx * hw, 0.95 * k, 0.0)
            self.J['knee' + s] = V(sx * (hw + 0.005), 0.52 * k, 0.025)
            self.J['ankle' + s] = V(sx * (hw + 0.008), 0.085 * k, -0.02)
            self.J['toe' + s] = V(sx * (hw + 0.012), 0.025, 0.15 * k)
        self.head_r = 0.103 * k * head_scale
        self.HC = self.J['head'] + V(0, self.head_r * 1.05, 0.012)   # head centre
        self.belly = belly
        self.bones = {}      # name -> (head, tail, parent)
        self.meshes = []     # (object, weighting) weighting: 'auto' | bone name (rigid) | callable(v) -> {bone: w}
        self.arm = None
        self._skeleton()

    # ---------------------------------------------------------------- skeleton
    def _skeleton(self):
        J = self.J
        b = self.bones
        b['hips'] = (J['hips'], J['waist'], None)
        b['spine'] = (J['waist'], J['chest'], 'hips')
        b['chest'] = (J['chest'], J['neck'], 'spine')
        b['neck'] = (J['neck'], J['head'], 'chest')
        b['head'] = (J['head'], J['crown'], 'neck')
        for s in 'LR':
            b['clavicle.' + s] = (J['clav' + s], J['shoulder' + s], 'chest')
            b['upper_arm.' + s] = (J['shoulder' + s], J['elbow' + s], 'clavicle.' + s)
            b['forearm.' + s] = (J['elbow' + s], J['wrist' + s], 'upper_arm.' + s)
            b['hand.' + s] = (J['wrist' + s], J['fingers' + s], 'forearm.' + s)
            b['thigh.' + s] = (J['hip' + s], J['knee' + s], 'hips')
            b['shin.' + s] = (J['knee' + s], J['ankle' + s], 'thigh.' + s)
            b['foot.' + s] = (J['ankle' + s], J['toe' + s], 'shin.' + s)

    def build_armature(self):
        ad = bpy.data.armatures.new(self.name + '_rig')
        arm = bpy.data.objects.new(self.name, ad)
        bpy.context.scene.collection.objects.link(arm)
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')
        for n, (h, t, p) in self.bones.items():
            eb = ad.edit_bones.new(n)
            eb.head = g(*h)
            eb.tail = g(*t)
            eb.roll = 0.0
            # keep every bone's local X along the character's left-right axis so pitch is a clean X rotation
            eb.align_roll(Vector((0, 0, 1)) if abs((eb.tail - eb.head).normalized().z) < 0.9 else Vector((0, -1, 0)))
        for n, (h, t, p) in self.bones.items():
            if p:
                ad.edit_bones[n].parent = ad.edit_bones[p]
        bpy.ops.object.mode_set(mode='OBJECT')
        self.arm = arm
        return arm

    # ---------------------------------------------------------------- weights
    def _seg_dist(self, p, a, b):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
        return (p - (a + ab * t)).length

    def auto_weights(self, p, allowed=None):
        """Skin weight from distance to bone segments, limited by side and region so arms don't pull the torso."""
        x, y = p.x, p.y
        side = 'L' if x > 0 else 'R'
        cand = []
        sw = abs(self.J['shoulderL'].x)
        if abs(x) > sw * 0.82 and y > self.J['hips'].y - 0.1 and y < self.J['neck'].y + 0.05:
            cand = ['clavicle.' + side, 'upper_arm.' + side, 'forearm.' + side, 'hand.' + side, 'chest']
            if abs(x) < sw:
                cand.append('spine')
        elif y < self.J['hips'].y - 0.02:
            cand = ['hips', 'thigh.' + side, 'shin.' + side, 'foot.' + side]
        else:
            cand = ['hips', 'spine', 'chest', 'neck', 'head', 'clavicle.' + side, 'thigh.' + side]
        if allowed:
            cand = [c for c in cand if c in allowed] or allowed
        ds = sorted(((self._seg_dist(p, self.bones[c][0], self.bones[c][1]), c) for c in cand))[:2]
        if len(ds) == 1 or ds[1][0] - ds[0][0] > 0.08:
            return {ds[0][1]: 1.0}
        w0, w1 = 1 / (ds[0][0] ** 3 + 1e-5), 1 / (ds[1][0] ** 3 + 1e-5)
        return {ds[0][1]: w0 / (w0 + w1), ds[1][1]: w1 / (w0 + w1)}

    def add(self, obj, weighting='auto'):
        self.meshes.append((obj, weighting))
        return obj

    def rigid(self, objs, bone, name):
        o = blib.merge([x for x in objs if x is not None], name)
        return self.add(o, bone)

    # ---------------------------------------------------------------- body
    def body(self, outfit, skin, legs=None, arms=None, chest_front=None, cuffs=None):
        """The clothed body: one smooth skin-modifier mesh from neck to ankles, coloured by region
        (torso = outfit, legs = trousers/stockings, arms = sleeves); bare hands and head are separate pieces."""
        J, k, bw = self.J, self.k, self.build
        f = 0.82 if self.female else 1.0
        pts = [J['hips'] + V(0, 0, -0.01), J['waist'], J['chest'] + V(0, 0, 0.005), J['neck'] + V(0, -0.02, 0), J['neck'] + V(0, 0.05, 0.005)]
        rad = [(0.155 * bw * (1.12 if self.female else 1), 0.12 * bw), (0.135 * bw * f + 0.04 * self.belly, 0.105 * bw + 0.06 * self.belly),
               (0.155 * bw * f, 0.11 * bw), (0.06, 0.055), (0.05, 0.048)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
        for s in 'LR':
            i0 = len(pts)
            pts += [J['shoulder' + s], J['elbow' + s], J['wrist' + s] + (J['elbow' + s] - J['wrist' + s]).normalized() * 0.015,
                    J['hip' + s], J['knee' + s], J['ankle' + s] + V(0, 0.01, 0)]
            rad += [0.058 * bw, 0.045 * bw, 0.037, (0.085 * bw * (1.08 if self.female else 1)), 0.058, 0.042]
            edges += [(2, i0), (i0, i0 + 1), (i0 + 1, i0 + 2), (0, i0 + 3), (i0 + 3, i0 + 4), (i0 + 4, i0 + 5)]
        me = bpy.data.meshes.new('Body')
        me.from_pydata([g(*(p * 1.0)) for p in pts], edges, [])
        o = bpy.data.objects.new('Body', me)
        bpy.context.scene.collection.objects.link(o)
        o.modifiers.new('skin', 'SKIN')
        sv = me.skin_vertices[0].data
        for i, r in enumerate(rad):
            sv[i].radius = r if isinstance(r, tuple) else (r, r)
        sv[0].use_root = True
        sub = o.modifiers.new('sub', 'SUBSURF')
        sub.levels = sub.render_levels = 2
        # bake the modifiers so we can colour faces by region and weight vertices
        dg = bpy.context.evaluated_depsgraph_get()
        nm = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        bpy.data.objects.remove(o, do_unlink=True)
        o = bpy.data.objects.new('Body', nm)
        bpy.context.scene.collection.objects.link(o)
        mats = [outfit, legs or outfit, arms or outfit, chest_front or outfit]
        for m in mats:
            nm.materials.append(m)
        hip_y = J['hips'].y - 0.03
        sw = abs(J['shoulderL'].x)
        for p in nm.polygons:
            c = p.center   # Blender coords: Godot x = c.x, y = c.z, z = -c.y
            gx, gy, gz = c.x, c.z, -c.y
            if gy < hip_y and abs(gx) < sw * 0.9:
                p.material_index = 1
            elif abs(gx) > sw * 0.92 and gy > hip_y:
                p.material_index = 2
            elif chest_front and gz > 0.04 and abs(gx) < 0.07 * self.build and J['waist'].y + 0.05 < gy < J['neck'].y - 0.01:
                p.material_index = 3
            p.use_smooth = True
        self.add(o, 'auto')
        return o

    def hands(self, skin, cuff=None, gloves=None):
        """Hands: palm, four fingers, thumb, gently curled; optional cuff of a sleeve."""
        for s, sx in (('L', 1), ('R', -1)):
            w, ft = self.J['wrist' + s], self.J['fingers' + s]
            d = (ft - w).normalized()
            side = V(0, 0, 1)
            m = gloves or skin
            parts = [sphere('palm', 0.042, w + d * 0.045, m, scale=(0.55, 1.15, 0.95), rot=(0, 0, math.degrees(math.atan2(d.x, -d.y)) * -1), segs=14, rings=10)]
            for i in range(4):
                off = side * (-0.022 + i * 0.0145)
                base = w + d * 0.085 + off
                tip = base + d * (0.06 - abs(i - 1.5) * 0.008) + V(0, 0, 0.012) + V(-sx * 0.006, 0, 0)
                parts.append(tube('finger', [base, base + (tip - base) * 0.55 + V(0, 0, 0.006), tip], [0.0085, 0.0078, 0.0068], m, segs=8))
            tb = w + d * 0.035 + side * 0.03
            parts.append(tube('thumb', [tb, tb + d * 0.03 + side * 0.012, tb + d * 0.055 + side * 0.01], [0.01, 0.009, 0.008], m, segs=8))
            if cuff:
                parts.append(cyl('cuff', 0.042, 0.04, 0.045, w - d * 0.01, cuff, rot=(math.degrees(math.atan2(d.z, -d.y)), 0, -math.degrees(math.atan2(d.x, -d.y))), segs=16))
            self.rigid(parts, 'hand.' + s, 'Hand_' + s)

    def shoes(self, m, boot=0.0, heel=0.0):
        for s in 'LR':
            a, t = self.J['ankle' + s], self.J['toe' + s]
            mid = (a + t) / 2
            parts = [blib.subsurf(box('shoe', (0.095, 0.075, (t - a).length + 0.1), (mid.x, 0.038, mid.z + 0.01), m, bevel=0.034, seg=2), 1)]
            if boot:
                parts.append(cyl('shaft', 0.05, 0.056, boot, (a.x, 0.06 + boot / 2, a.z - 0.005), m, segs=18))
            if heel:
                parts.append(box('heel', (0.06, heel, 0.06), (a.x, heel / 2, a.z - 0.04), m))
            self.rigid(parts, 'foot.' + s if not boot else 'shin.' + s, 'Shoe_' + s)
            if boot:  # the foot part of the boot follows the foot
                pass

    # ---------------------------------------------------------------- head
    def head(self, skin, lips, hair_col, iris='#3a2a1c', brow_col=None, kohl=False, age=None):
        """The modelled head (jaw, eye sockets, nose, lidded eyes with iris/pupil/catchlight, brows, ears, lips).
        Returns landmarks (Godot metres) for placing hair and hats."""
        age = self.age if age is None else age
        R = self.head_r
        HC = self.HC

        def hc(x, y, z):
            return HC + V(x, y, z) * (R / 0.115)

        sk = sphere('skull', R, HC, skin, scale=(0.9, 1.08, 1.0), segs=36, rings=22)
        fem = self.female

        def shape(x, y, z):
            r = R
            t = max(0.0, -y / r)
            kx = 1 - (0.36 if fem else 0.3) * t ** 1.4
            x, z = x * kx, z * (1 - 0.15 * t ** 2)
            if z > 0 and t > 0.4:
                z += r * (0.08 if not fem else 0.05) * (t - 0.4)
            if z < 0:
                z *= 1.06
            if y > 0.02 * r / 0.115 and z > 0.04 * r / 0.115:
                z -= 0.07 * r * (y / r)
            if z > 0:
                for ex in (-0.04, 0.04):
                    exs = ex * r / 0.115
                    z -= 0.013 * r / 0.115 * math.exp(-((x - exs) ** 2 + (y - 0.01 * r / 0.115) ** 2 * 1.6) / (0.00035 * (r / 0.115) ** 2))
                z += 0.005 * r / 0.115 * math.exp(-((y - 0.04 * r / 0.115) ** 2) / (0.0002 * (r / 0.115) ** 2)) * math.exp(-(x ** 2) / (0.004 * (r / 0.115) ** 2))
                if age > 55:   # hollower cheeks, deeper nasolabial line
                    z -= 0.004 * r / 0.115 * math.exp(-((abs(x) - 0.045 * r / 0.115) ** 2 + (y + 0.035 * r / 0.115) ** 2) / (0.0004 * (r / 0.115) ** 2))
            return x, y, z
        deform(sk, shape)
        P = [sk]
        P.append(tube('nose', [hc(0, 0.02, 0.098), hc(0, -0.01, 0.112), hc(0, -0.035, 0.122)], [0.011 * R / 0.115, 0.014 * R / 0.115, 0.016 * R / 0.115], skin, segs=12))
        P.append(sphere('nose_tip', 0.016 * R / 0.115, hc(0, -0.037, 0.118), skin, scale=(1.25, 0.85, 1), segs=14, rings=8))
        for sx in (-1, 1):
            P.append(sphere('nostril', 0.009 * R / 0.115, hc(sx * 0.014, -0.042, 0.112), skin, scale=(1.2, 0.8, 1), segs=10, rings=6))
        eyew = mat('EyeWhite', '#efeae2', 0.15)
        irism = mat('Iris_' + iris, iris, 0.1)
        for sx in (-1, 1):
            ex = sx * 0.04
            P.append(sphere('eye', 0.0185 * R / 0.115, hc(ex, 0.011, 0.088), eyew, segs=18, rings=12))
            P.append(sphere('iris', 0.0105 * R / 0.115, hc(ex, 0.011, 0.1035), irism, scale=(1, 1, 0.4), segs=16, rings=8))
            P.append(sphere('pupil', 0.0052 * R / 0.115, hc(ex, 0.011, 0.1072), mat('Pupil', '#070707', 0.05), scale=(1, 1, 0.4), segs=10, rings=6))
            P.append(sphere('glint', 0.0022 * R / 0.115, hc(ex + 0.004, 0.015, 0.1085), mat('Glint', '#ffffff', 0.1, emit='#ffffff', strength=1.5), segs=6, rings=4))
            lid = sphere('lid', 0.0205 * R / 0.115, hc(ex, 0.011, 0.088), mat('Kohl', '#141010', 0.4) if kohl else skin, segs=18, rings=12)
            delete_verts(lid, lambda x, y, z: y < 0.009 * R / 0.115 * (0.6 if age > 60 else 1.0))
            P.append(solidify(lid, 0.0025))
            low = sphere('lowlid', 0.0198 * R / 0.115, hc(ex, 0.011, 0.088), skin, segs=18, rings=12)
            delete_verts(low, lambda x, y, z: y > -0.012 * R / 0.115)
            P.append(solidify(low, 0.002))
            P.append(sphere('ear', 0.03 * R / 0.115, hc(sx * 0.1, 0.0, -0.005), skin, scale=(0.38, 1.1, 0.72), segs=12, rings=8))
            P.append(torus('ear_rim', 0.022 * R / 0.115, 0.004 * R / 0.115, hc(sx * 0.105, 0.0, -0.005), skin, rot=(0, 90, 0), scale=(1, 1.4, 1), segs=16, rsegs=5))
            brow = mat('Brow_' + (brow_col or hair_col), brow_col or hair_col, 0.8)
            thick = 0.0075 if not fem else 0.005
            P.append(tube('brow', [hc(sx * 0.016, 0.042, 0.104), hc(sx * 0.04, 0.05, 0.103), hc(sx * 0.064, 0.043, 0.093)], thick * R / 0.115, brow, segs=6))
        P.append(sphere('upper_lip', 0.025 * R / 0.115, hc(0, -0.064, 0.104), lips, scale=(1, 0.27, 0.42), segs=16, rings=8))
        P.append(sphere('lower_lip', 0.022 * R / 0.115, hc(0, -0.075, 0.103), lips, scale=(1, 0.33, 0.46), segs=16, rings=8))
        P.append(cyl('neck', 0.05 * self.k, 0.046 * self.k, (HC.y - R * 0.6) - self.J['neck'].y + 0.02, V(0, (HC.y - R * 0.6 + self.J['neck'].y) / 2, -0.02), skin, segs=18))
        self.rigid(P, 'head', 'Head')
        return {'hc': hc, 'R': R, 'top': HC.y + R * 1.08, 'front': HC.z + R * 0.92}

    # ---------------------------------------------------------------- costume helpers
    def skirt(self, name, m, top_y, bottom_y, r_top, r_bottom, depth=0.8, segs=36, rings=10, back_only=False, front_only=False, over=None):
        """A skirt or robe hem: a loft from the waist down, weighted to the hips and (toward the hem) the legs."""
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new('UVMap')
        grid = []
        for r in range(rings + 1):
            t = r / rings
            y = top_y + (bottom_y - top_y) * t
            rad = r_top + (r_bottom - r_top) * (t ** 1.3)
            if y < self.J['waist'].y - 0.04:   # always clear the hips and thighs
                rad = max(rad, abs(self.J['hipL'].x) + 0.095 * self.build + 0.03)
            if over is not None:               # an apron lies just over another skirt
                rad = over(y) + 0.014
            row = []
            for s in range(segs + 1):
                a = math.tau * s / segs
                if back_only:
                    a = math.pi + (a - math.pi) * 0.55     # only the back half: coat tails
                if front_only:
                    a = (a - math.pi) * 0.3                # only the front: an apron
                ripple = 1 + 0.035 * math.sin(a * 9) * t
                row.append(bm.verts.new(g(math.sin(a) * rad * ripple, y, math.cos(a) * rad * depth * ripple - 0.01)))
            grid.append(row)
        for r in range(rings):
            for s in range(segs):
                f = bm.faces.new((grid[r][s], grid[r][s + 1], grid[r + 1][s + 1], grid[r + 1][s]))
                f.smooth = True
                for loop, (u, v) in zip(f.loops, ((s, r), (s + 1, r), (s + 1, r + 1), (s, r + 1))):
                    loop[uvl].uv = (u / segs * 4, v / rings * 2)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        me.materials.append(m)
        solidify(o, 0.008)
        J = self.J
        prof = (top_y, bottom_y, r_top, r_bottom)

        def radius_at(y, prof=prof):
            t0, t1, a, b = prof
            t = max(0.0, min(1.0, (y - t0) / (t1 - t0)))
            r = a + (b - a) * t ** 1.3
            if y < self.J['waist'].y - 0.04:
                r = max(r, abs(self.J['hipL'].x) + 0.095 * self.build + 0.03)
            return r
        self.last_skirt = radius_at

        def w(p):
            # skirts follow the legs: the front over the thighs (and from the knee, the shins), the back hangs from
            # the hips. A seated skirt then drapes over the lap and falls from the knees instead of stretching.
            side = 'L' if p.x > 0 else 'R'
            if p.y > J['hips'].y - 0.04:
                return {'hips': 1.0}
            leg_x = J['hip' + side].x
            q = V(leg_x + (p.x - leg_x) * 0.3, p.y, 0.0)
            lw = self.auto_weights(q, allowed=['thigh.' + side, 'shin.' + side])
            front = max(0.0, min(1.0, (p.z + 0.04) / 0.12))
            share = 0.25 + 0.7 * front
            out = {b: x * share for b, x in lw.items()}
            out['hips'] = out.get('hips', 0.0) + 1 - share
            return out
        return self.add(o, w)

    def finish(self):
        """Weights every mesh and parents it to the armature."""
        arm = self.arm
        for o, how in self.meshes:
            groups = {}

            def grp(n):
                if n not in groups:
                    groups[n] = o.vertex_groups.new(name=n)
                return groups[n]
            for v in o.data.vertices:
                p = V(v.co.x, v.co.z, -v.co.y)
                if isinstance(how, str) and how != 'auto':
                    wts = {how: 1.0}
                elif callable(how):
                    wts = how(p)
                else:
                    wts = self.auto_weights(p)
                for bn, x in wts.items():
                    grp(bn).add([v.index], x, 'REPLACE')
            o.parent = arm
            m = o.modifiers.new('rig', 'ARMATURE')
            m.object = arm
        return [o for o, _ in self.meshes]


def torus(name, R, r, loc, material, **kw):
    return blib.torus(name, R, r, loc, material, **kw)


# ==================================================================== animation
FPS = 30


def _bone_mat(arm, bn):
    return arm.data.bones[bn].matrix_local.to_3x3()


def pose(arm, values, frame):
    """values: {bone: (rx, ry, rz) degrees about Godot axes, applied in the bone's rest frame relative to its
    parent's pose; 'hips@loc': (dx, dy, dz) metres}."""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        rot = values.get(pb.name, (0, 0, 0))
        R = (Matrix.Rotation(math.radians(rot[2]), 3, Vector((0, -1, 0))) @ Matrix.Rotation(math.radians(rot[1]), 3, Vector((0, 0, 1)))
             @ Matrix.Rotation(math.radians(rot[0]), 3, Vector((1, 0, 0))))
        M = _bone_mat(arm, pb.name)
        q = (M.inverted() @ R @ M).to_quaternion()
        pb.rotation_quaternion = q
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if pb.name == 'hips':
            loc = values.get('hips@loc', (0, 0, 0))
            pb.location = M.inverted() @ g(*loc)
            pb.keyframe_insert('location', frame=frame)


def action(arm, name, frames):
    """frames: list of (frame, values). Creates an action, keys it and stores it with a fake user."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    for f, vals in frames:
        pose(arm, vals, f)
    try:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
    except Exception:
        pass
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, int(frames[0][0]), act)
    arm.animation_data.action = None
    return act


def standard_actions(person):
    arm = person.arm
    k = person.k
    A = {'upper_arm.L': (0, 0, 6), 'upper_arm.R': (0, 0, -6), 'forearm.L': (-12, 0, 0), 'forearm.R': (-12, 0, 0)}

    def merge(*ds):
        out = {}
        for d in ds:
            for kk, v in d.items():
                if kk in out and kk != 'hips@loc':
                    out[kk] = tuple(a + b for a, b in zip(out[kk], v))
                else:
                    out[kk] = v
        return out
    # idle: slow breathing and weight shift
    action(arm, 'idle', [(0, merge(A, {'chest': (0, 0, 0)})), (45, merge(A, {'chest': (-2, 0, 0), 'head': (2, 0, 0), 'hips@loc': (0.006, 0, 0)})),
                         (90, merge(A, {'chest': (0, 0, 0)}))])
    # walk cycle
    def step(ph):
        s = math.sin(ph)
        c = math.cos(ph)
        return merge(A, {
            'thigh.L': (-24 * s, 0, 0), 'thigh.R': (24 * s, 0, 0),
            'shin.L': (max(0, 40 * c) + 6, 0, 0), 'shin.R': (max(0, -40 * c) + 6, 0, 0),
            'foot.L': (-6 * s, 0, 0), 'foot.R': (6 * s, 0, 0),
            'upper_arm.L': (18 * s, 0, 0), 'upper_arm.R': (-18 * s, 0, 0),
            'forearm.L': (-10 - 8 * max(0, -s), 0, 0), 'forearm.R': (-10 - 8 * max(0, s), 0, 0),
            'spine': (2, 4 * s, 0), 'chest': (0, -6 * s, 0),
            'hips@loc': (0, -0.018 * abs(c) * k, 0)})
    action(arm, 'walk', [(f, step(f / 32 * math.tau)) for f in range(0, 33, 4)])
    # sitting on a bench (seat top ~0.47 m): hips drop and move back
    hip_drop = person.J['hips'].y - 0.53
    SIT = merge({'thigh.L': (-86, 0, -3), 'thigh.R': (-86, 0, 3), 'shin.L': (88, 0, 0), 'shin.R': (88, 0, 0), 'foot.L': (-4, 0, 0), 'foot.R': (-4, 0, 0),
                 'spine': (4, 0, 0), 'chest': (2, 0, 0), 'hips@loc': (0, -hip_drop, -0.02),
                 'upper_arm.L': (-28, 0, 10), 'upper_arm.R': (-28, 0, -10), 'forearm.L': (-52, 0, -8), 'forearm.R': (-52, 0, 8)})
    action(arm, 'sit', [(0, SIT), (45, merge(SIT, {'chest': (-2, 0, 0)})), (90, SIT)])
    # talking while seated / standing: an open-handed gesture
    def gesture(base, amt):
        return merge(base, {'upper_arm.R': (-20 * amt, 0, -8 * amt), 'forearm.R': (-45 * amt, 20 * amt, 0), 'hand.R': (0, 0, -15 * amt), 'head': (4 * amt, 6 * amt, 0)})
    action(arm, 'sit_talk', [(0, gesture(SIT, 0.2)), (20, gesture(SIT, 1.0)), (40, gesture(SIT, 0.5)), (60, gesture(SIT, 1.0)), (80, gesture(SIT, 0.2))])
    action(arm, 'talk', [(0, gesture(A, 0.2)), (20, gesture(A, 1.0)), (40, gesture(A, 0.5)), (60, gesture(A, 1.0)), (80, gesture(A, 0.2))])
    # leaning on the table, arms forward (dining car)
    TABLE = merge(SIT, {'upper_arm.L': (-55, 0, 6), 'upper_arm.R': (-55, 0, -6), 'forearm.L': (-50, 0, -10), 'forearm.R': (-50, 0, 10), 'chest': (6, 0, 0)})
    action(arm, 'sit_table', [(0, TABLE), (45, merge(TABLE, {'chest': (-2, 0, 0)})), (90, TABLE)])
    # lying asleep (berths): flat on the back
    action(arm, 'lie', [(0, merge({'hips@loc': (0, -person.J['hips'].y + 0.62, 0)}, {'thigh.L': (0, 0, -2), 'thigh.R': (0, 0, 2)})),
                        (1, merge({'hips@loc': (0, -person.J['hips'].y + 0.62, 0)}, {'thigh.L': (0, 0, -2), 'thigh.R': (0, 0, 2)}))])


def export(person, path):
    objs = [person.arm] + [o for o, _ in person.meshes]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = person.arm
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=False, export_yup=True,
                              export_skins=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_materials='EXPORT', export_extras=False, export_lights=False, export_cameras=False)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o, _ in person.meshes)
    print(f'exported {path}: {tris} tris')
