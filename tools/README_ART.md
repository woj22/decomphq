# Art pipeline

## Run
- `python3 tools/build_assets.py` regenerates everything under `game/assets/` (tiles, walls, props, characters, fx, backdrops, ui, portraits, audio) in about 20 s on 4 CPUs. It fails if a pixel is off-palette, a sprite ID is missing, or a prop or character touches its canvas edge. `--keep-raw DIR` keeps the unquantised Blender renders.
- `python3 tools/procgen/fetch_fonts.py` fetches the fonts once (needs network). The fonts are committed.
- `python3 tools/preview_area.py game/data/areas/area_clerks_court.json out.png [--scale 2] [--no-crowd]` composes an area the way the Engine does. It also accepts a plain ASCII grid file.

## Layout
- `tools/blender/lib.py` sets up the Cycles CPU scene, the orthographic 2:1 camera and the primitives. `kit.py` builds the architecture and props, `rig.py` builds the hooded character rig and `jobs.py` runs the render worker. The Blender jobs run in parallel processes.
- `tools/procgen/spec.py` holds every sprite's ID, size, origin, kind and frames (the single source for both sides). `palette.py` holds Border-24 and the UI tokens. `post.py` quantises, outlines, packs and lints. `tiles.py` draws floors, decals and FX in numpy. `backdrops.py`, `ui.py` and `audio.py` make the rest.

## Add a sprite
1. Add an `S('id', group, (w,h), origin, kind, job='...')` line to `spec.py`. The origin is the pixel on the cell centre at floor level, or on the feet for characters.
2. Blender sprite: write a builder in `kit.py` in the cell-local frame. The cell centre is the world origin, +X is screen SE, +Y is screen NE and 1 BU is one tile. Call it from a job in `jobs.py` with `shot(ctx, 'id')`, and add the job to `JOBS` in `build_assets.py` if it is new. Numpy/PIL sprite: use `src='pil'` and draw it in `pil_tiles` or `ui.py`.
3. Run the build, then check the result with `preview_area.py`.

## Palette rules
- World sprites may use Border-24 only (PROJECT §7.1), and the build fails otherwise. Soul colours appear only in soul sprites. The emissive colours `fff3c4 f6d67a e8552b` appear only where the render was emissive.
- The ambient tint `#9e94cc` is multiplied into non-emissive pixels, with exposure gain 1.45, then each pixel takes the nearest Border-24 colour (luma-weighted). There is no dithering on sprites. Bayer dithering is used on backdrops only.
- Characters and props get a 1 px `#0d0b12` outline (souls `#6a5484`, 75 % alpha baked in). Floors and walls get no outline.
- UI and portraits may also use the §9.5 UI tokens. `#8b3fd9` is used only for `stamp_rm0`.
- Brick courses are 6 px. Patterns must have a period of 1 tile (brick width 1/3 BU) so walls tile without seams.
