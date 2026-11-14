# Roman city vista: Blender pipeline

The balcony-over-the-capital scene is rebuilt from code in stages, so it can be re-run and adjusted.
Reference: `imperium/reference/balcony_target.png` (16:9; the camera is framed to match it).

## Running

```
cd imperium/blender
python3 rc_build.py --stage greybox --level preview        # simple masses, 768x432
python3 rc_build.py --stage full    --level development    # all assets, 1536x864
python3 rc_build.py --stage full    --level final --save-final   # 3072x1728 + blend/roman_city_final.blend
```

Each run saves an incremental `blend/roman_city_vNN_<stage>.blend` (`--no-save` skips it), renders
`renders/rc_<stage>_<level>.png` and writes `renders/compare_rc_<stage>.png` beside the reference.
`rc_audit.py` is the Stage 1 audit of the earlier scene; its backup is `blend/roman_city_v01_backup_original.blend`.

## Modules (one per production stage)

| Module | Stage | Builds |
|---|---|---|
| `rc_common.py` | all | parameters, collections, `terrain_z(x, y)`, camera constants, incremental save |
| `rc_terrain.py` | 3 | faceted heightfield over the view wedge (temple hill, rolling districts, outskirts rise) |
| `rc_assets.py` | 4 | the hidden **Asset Library** collection (see below) |
| `rc_city.py` | 5–6 | streets, squares, districts, lot packing, instancing, forum, landmark temple, aqueduct, theatre |
| `rc_foreground.py` | 7 | tiled terrace, balustrade, Ionic loggia, laurel banners, spear statue, brazier, court |
| `rc_atmos.py` | 9 | sun + world gradient, sun disc, low mountains, angular cloud banks, distance haze, camera |
| `rc_build.py` | – | runs the stages in order, saves, renders, compares |

## Scene hierarchy

```
Terrain                  heightfield
Streets & Plazas         paved avenues, rings, squares
Residential              linked duplicates of small / medium / large / mid / far assets, landmark palaces
Public Buildings         basilicas, baths, theatres, stoas, rotundas, forum colonnades
Temples & Monuments      landmark temple precinct, temples, columns, obelisks, fountains
Towers & Arches          towers, arches, city gate, aqueduct spans
Vegetation               cypresses, pines, gardens
Foreground               terrace, balustrade, loggia, banners, statue, brazier (+ fire light)
Characters               the ruler (royal cloak) and court
Lighting & Atmosphere    sun, sky fill, world, mountains, clouds, sun disc, camera
Asset Library (hidden)   master meshes: every city building is an object sharing one of these meshes
```

Asset library: residential small ×8, medium ×8, large ×5; temples ×4; towers ×4; public ×5;
arches/gateways ×4; monuments ×3; trees ×4; plus LOD sets (mid ×8, far ×6, skyline ×3).
A full build places about 17,000 instances that share about 70 meshes.

## Adjusting it (`city_params.json`)

- **Density:** `lot_attempts` (overall), `density.near/mid/far` (acceptance per depth band),
  `near_limit_m` and `mid_limit_m` (where detailed and mid-LOD assets give way), `alleys`, `squares`, `tree_density`.
- **Building variation:** `height_scale` and `footprint_scale` (per-instance random ranges), and `mix_near` (the share of
  small / medium / large / public / temple / tower / garden / monument in the detailed band).
  New designs go in the `build_*` functions in `rc_assets.py`. Each one registers itself with `_new(category, …)`.
- **Landmarks:** `landmark_temple.x/y/hill/scale` (the temple precinct and its hill), and `forum.x/y`.
  The palaces, aqueduct, gate and theatre are near the end of `rc_city.build_city`.
- **Atmosphere:** `haze.start_m/end_m/max/colour`. The cloud banks are the `banks` list in `rc_atmos.clouds`
  (bearing, elevation, length, height).
- **Reproducibility:** `seed` (the city layout), `rc_assets.build_library(seed)` (the asset designs), and
  `rc_atmos.build_atmosphere(seed=…)` (the mountains).
- **Camera:** `rc_common.CAM_LOC / CAM_PITCH_DEG / CAM_LENS`. These are matched to the reference; change them with care.
