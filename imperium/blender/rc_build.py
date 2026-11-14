"""Stage orchestrator for the Roman city vista.

  python3 rc_build.py --stage greybox  --level preview
  python3 rc_build.py --stage full     --level development
  python3 rc_build.py --stage full     --level final --save-final

Stages run in order: terrain -> assets -> city -> foreground -> atmosphere -> haze -> camera.
'greybox' uses simple far-LOD blocks for the whole city. Each run saves an incremental .blend,
renders the camera at the requested level, and writes a side-by-side comparison with the reference.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import rc_common as R  # noqa: E402
import rc_terrain  # noqa: E402
import rc_assets  # noqa: E402
import rc_city  # noqa: E402
import rc_foreground  # noqa: E402
import rc_atmos  # noqa: E402

SAMPLES = {"preview": 16, "development": 48, "final": 48}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="full", choices=["greybox", "full"])
    ap.add_argument("--level", default="preview", choices=list(R.LEVELS))
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--save-final", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in R.COLLECTIONS:
        R.coll(c)
    rc_terrain.build_terrain()
    lib = rc_assets.build_library()
    rc_city.build_city(lib, greybox=(a.stage == "greybox"))
    rc_foreground.build_foreground()
    rc_atmos.build_atmosphere(a.samples or SAMPLES[a.level])
    rc_atmos.apply_haze()
    rc_atmos.camera(R.LEVELS[a.level])
    # hide the library masters from the render (instances share their meshes)
    for o in R.coll("Asset Library").objects:
        o.hide_render = True
        o.hide_viewport = True
    sc = bpy.context.scene
    faces = sum(len(o.data.polygons) for o in sc.objects if o.type == "MESH" and not o.hide_render)
    inst = sum(1 for c in ("Residential", "Public Buildings", "Temples & Monuments", "Towers & Arches", "Vegetation") for o in R.coll(c).objects)
    print("STATS objects %d instances %d faces(rendered, incl. instances) %d build %.0fs" % (len(sc.objects), inst, faces, time.time() - t0))
    if not a.no_save:
        R.save(a.stage)
    if a.save_final:
        p = os.path.join(R.ROOT, "blend", "roman_city_final.blend")
        bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    out = os.path.join(R.ROOT, "renders", "rc_%s_%s.png" % (a.stage, a.level))
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("render", out, "%.0fs" % (time.time() - t0))
    subprocess.run([sys.executable, os.path.join(R.HERE, "compare.py"), os.path.join(R.ROOT, "reference", "balcony_target.png"), out,
                    os.path.join(R.ROOT, "renders", "compare_rc_%s.png" % a.stage)])


if __name__ == "__main__":
    main()
