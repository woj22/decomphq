# Alien Planet: environment prototype

A small, explorable, low-poly alien world. It is made procedurally in **Blender** and played in **Godot 4.6** (Compatibility renderer, so it runs on mobile). There is no gameplay yet. This prototype is only the world and its look.

![spawn](screenshots/01_spawn.jpg)

## What's in it
- **Terrain:** a ~180 m explorable bowl enclosed by terraced, strata-banded cliffs. It also has four stepped mesas, wind-carved ridges and a lake basin with a sandy shelf.
- **Unusual landforms:** **floating rock islands** with plants on top (they bob slowly), a huge **natural rock arch**, a **hexagonal basalt column field**, curved **thorn spires** and balanced **hoodoo** stacks.
- **Alien vegetation:**
  - magenta/coral **parasol trees** with hanging bioluminescent seed bulbs
  - **bulb pods**, teal **fan fronds** and amber **tube coral**
  - **lantern stalks** and **glowing crystal clusters**
  - tri-colour grass tufts
  - all plants sway in the wind on the GPU
- **Ancient ruins:**
  - a **ring shrine** on the temple mesa: a broken standing stone ring with a floating glowing core, a monolith circle and grand stairs
  - a ruined **colonnade** with fallen pillars
  - a half-sunk **gateway**
  - glyph-lit **monoliths** and wall fragments
- **Water:** stylised low-poly lake water that matches the faceted world. It has a gently rolling faceted surface, sparkling sun glints and a soft sky reflection. It is clearly transparent: the sandy bed, rocks, weed, coral and crystals show through, tinted from turquoise to deep blue with depth. Crisp foam rings lap the shore and the coral that breaks the surface.
- **Sky:** a natural dusk gradient with a low sun and halo, a small moon and faint stars. It is all analytic in one shader, with no textures.
- **Atmosphere:** height + distance fog with sun scatter, soft glow on emissives, drifting spore particles and baked ambient occlusion.

## Explore it
Open `alien_planet/godot/` in Godot 4.6 and press Play.

| | Desktop | Touch |
|---|---|---|
| Move | WASD / arrows (Shift = run) | left-side floating stick (push to the edge to run) |
| Look | click to capture the mouse, then move it (Esc releases) | drag on the right side |
| Jump | Space | JUMP |
| Fly camera | F (Space/Ctrl = up/down) | FLY (JUMP = rise) |

**Android:** run `tools/build_apk.sh --setup` once to install the SDK, templates and debug keystore. Then `alien_planet/build_apk.sh` produces `dist/alien-planet-debug.apk`, which you can sideload with `adb install -r`.

## Pipeline
```
python3 alien_planet/blender/build_world.py     # (pip bpy 5.x) or: blender -b -P alien_planet/blender/build_world.py
  -> alien_planet/blender/alien_world.blend      open/inspect/edit in Blender (camera is at the spawn point)
  -> alien_planet/godot/assets/world.glb         loaded by Godot at runtime
alien_planet/shots.sh OUTDIR [WxH] [--touch]    renders the screenshot gallery headlessly
```
- `blender/build_world.py` holds the whole world: layout constants at the top, then terrain, rocks, flora, ruins, floating islands, scatter, the AO bake and the export. The seed is fixed, so builds are reproducible. A full build takes about 2 s.
- `godot/scripts/main.gd` sets up materials, collision, sky/sun/fog, the lake and the explorer. `explorer.gd` is the first-person controller. `touch_controls.gd` holds the touch stick and buttons plus the HUD.
- `godot/shaders/`:
  - `solid` for terrain, rocks and ruins
  - `flora` for sway and leaf translucency
  - `glow` for unshaded pulsing emissives
  - `water` for the transparent lake (waves, depth tint, foam)
  - `sky` for the dusk sky

### Naming conventions (Blender object → Godot behaviour)
| Prefix | Behaviour |
|---|---|
| `Terrain`, `Rock_*`, `Ruin_*` | trimesh collision |
| `Flora_*` | wind sway (UV.x = sway weight, UV.y = phase), no collision |
| `Deco_*` | non-solid stone: stair treads over a ramp, rubble, glyphs |
| `Detail_*` | grass tufts, hidden beyond 48 m, no shadows |
| `Float_*` | floating islands; `Float_core` spins above the shrine with a light |

## Mobile budget (current)
- ~70k triangles in the whole world, in 58 merged objects chunked on a 4×4 grid so the engine can frustum-cull them.
- Typically 50–150 draw calls per frame, shadow pass included.
- No textures at all. Colour is per-face vertex colour, and ambient occlusion is baked into it, so it costs nothing at runtime.
- 5 shader materials plus the water (one transparent ~13k-triangle plane, which reads the depth buffer), 1 shadowed directional light (2 cascades, 80 m), 1 unshadowed fill light and 1 omni light.
- The sky is static, so its radiance and ambient are computed once.
- Not yet profiled on a real device. Levers if needed: `directional_shadow_max_distance`, the `Detail_` visibility range, the Glow setting, and `scaling_3d_scale`.

## Next steps (when expanding)
More biomes beyond the rim (the colour scheme here is this region's identity), a day/dusk cycle, mesh LODs or impostors for distant chunks, ambient audio, and streaming chunks for a bigger map.
