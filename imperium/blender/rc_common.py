"""Shared foundations for the Roman city project: parameters, collections, terrain height, camera.

Every stage module (rc_assets, rc_terrain, rc_city, rc_foreground, rc_atmos) imports this.
World axes: the balcony floor is z = 0; the camera looks along -Y; screen-right is -X.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARAMS = json.load(open(os.path.join(HERE, "city_params.json")))

CITY = -40.0                    # base city ground relative to the balcony floor
CAM_LOC = (0.0, 0.0, 2.86)
CAM_PITCH_DEG = -5.0
CAM_LENS = 24.0
REF_RES = (1672, 941)           # the reference image is 16:9 (1672 x 941)
LEVELS = {"preview": (768, 432), "development": (1536, 864), "final": (3072, 1728)}

COLLECTIONS = ["Terrain", "Streets & Plazas", "Residential", "Public Buildings", "Temples & Monuments", "Towers & Arches",
               "Vegetation", "Foreground", "Characters", "Lighting & Atmosphere", "Asset Library"]


def coll(name):
    """Get or create a top-level collection (no duplicates on re-runs)."""
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in [ch.name for ch in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(c)
    return c


def clear(name):
    """Remove a stage's objects so the stage can be rebuilt without touching the rest of the scene."""
    c = bpy.data.collections.get(name)
    if c is None:
        return
    for o in list(c.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for ch in list(c.children):
        bpy.data.collections.remove(ch)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def move_to(obj, cname):
    c = coll(cname)
    for uc in list(obj.users_collection):
        uc.objects.unlink(obj)
    c.objects.link(obj)
    for ch in obj.children:
        move_to(ch, cname)
    return obj


def gauss(x, y, cx, cy, r, h):
    return h * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))


def terrain_z(x, y):
    """Gentle, irregular city ground: a raised temple hill, a lifted forum, low neighbourhoods,
    and hills rising toward the outskirts. The palace hill climbs to the balcony near the camera."""
    lt = PARAMS["landmark_temple"]
    fo = PARAMS["forum"]
    z = CITY
    z += gauss(x, y, lt["x"], lt["y"], 170, lt["hill"])
    z += gauss(x, y, fo["x"], fo["y"], 90, 3.0)
    z += gauss(x, y, 170, -420, 260, -3.5)
    z += gauss(x, y, 330, -950, 320, 16)
    z += gauss(x, y, -560, -1250, 380, 20)
    z += gauss(x, y, 900, -2300, 600, 26)
    z += gauss(x, y, -1300, -2900, 700, 34)
    d = math.hypot(x, y)
    if d > 3200:
        z += (d - 3200) * 0.012
    z += gauss(x, y, -2600, -5600, 1600, 110) + gauss(x, y, 2300, -6200, 1800, 140)
    z += 1.6 * math.sin(x / 37.0) * math.cos(y / 53.0) + 1.1 * math.sin((x + y) / 91.0)
    # the palace hill under the balcony
    if y > -70:
        t = max(0.0, min(1.0, (y + 70) / 58.0))
        z = z + (-12.0 - z) * (t * t * (3 - 2 * t))
    return z


def save(stage):
    """Save an incremental project file: blend/roman_city_vNN_<stage>.blend."""
    d = os.path.join(ROOT, "blend")
    os.makedirs(d, exist_ok=True)
    n = 1 + max([int(f.split("_v")[1][:2]) for f in os.listdir(d) if f.startswith("roman_city_v") and f.endswith(".blend")] or [0])
    path = os.path.join(d, "roman_city_v%02d_%s.blend" % (n, stage))
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, "%.1f MB" % (os.path.getsize(path) / 1e6))
    return path
