"""Stage 1: rebuild the existing vista scene, report on it, and save it as the backup project file."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rc_common as R  # noqa: E402
import vista as V  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
rng = random.Random(21)
V.plan_city(rng)
V.horizon(rng)
V.balcony(rng)
V.court()
V.lighting(16)
V.apply_haze()
cam = V.camera(R.REF_RES)
sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == "MESH"]
faces = sum(len(o.data.polygons) for o in meshes)
xs = [v for o in meshes if o.name.startswith("Vista") for v in (o.bound_box[0][0], o.bound_box[6][0])]
ys = [v for o in meshes if o.name.startswith("Vista") for v in (o.bound_box[0][1], o.bound_box[6][1])]
print("AUDIT blender", bpy.app.version_string)
print("AUDIT camera loc", tuple(round(v, 2) for v in cam.location), "rot deg", tuple(round(math.degrees(v), 1) for v in cam.rotation_euler),
      "lens", cam.data.lens, "res", sc.render.resolution_x, sc.render.resolution_y)
print("AUDIT objects", len(sc.objects), "meshes", len(meshes), "faces", faces, "materials", len(bpy.data.materials))
print("AUDIT city extent x %.0f..%.0f  y %.0f..%.0f" % (min(xs), max(xs), min(ys), max(ys)))
print("AUDIT lights", [(o.name, o.data.type, round(o.data.energy, 2)) for o in sc.objects if o.type == "LIGHT"])
print("AUDIT merged city meshes (not instanced):", len([o for o in meshes if o.name.startswith("Vista")]))
R.save("backup_original")
