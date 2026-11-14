# Imperium (restarted with a Blender pipeline)

Characters and environments are modelled with Blender scripts (`blender/`, run with the `bpy` module:
`pip install bpy==5.3.0`), exported as `.glb` into `assets/`, and rendered previews go to `renders/`.

- `blender/kharad.py`: Thrask, a Kharad warrior-king (faceted low-poly creature body, bronze kit,
  cloak, iron crown). `python3 imperium/blender/kharad.py [--samples 64]`
- `blender/kharad_head.py`: the Kharad head hand-modelled vertex by vertex (cross-section slices,
  hinged jaw, surface-placed eyes and brows, square-section horns, fitted crown), flat colours.
  `python3 imperium/blender/kharad_head.py` -> `renders/kharad_head_sheet.png`
- `blender/cast.py`: the whole court (19 characters, four species) from one data table, hand-placed
  low-poly bodies, species heads, outfits, crowns, cloaks and props. Exports `assets/characters/<id>.glb`
  and renders group line-ups to `renders/cast_<group>.png`. `python3 imperium/blender/cast.py [--only a,b] [--turn]`
