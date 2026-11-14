# Imperium (restarted with a Blender pipeline)

Characters and environments are modelled with Blender scripts (`blender/`, run with the `bpy` module:
`pip install bpy==5.3.0`), exported as `.glb` into `assets/`, and rendered previews go to `renders/`.

- `blender/kharad.py`: Thrask, a Kharad warrior-king (faceted low-poly creature body, bronze kit,
  cloak, iron crown). `python3 imperium/blender/kharad.py [--samples 64]`
