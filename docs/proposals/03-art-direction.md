# 03 — Environment & Art Direction (Agent 3)

Status: proposal. Pipeline sections are a **recommendation with evidence** for the Technical Architect, who owns final standards.
Every number marked ✔ was measured in a throwaway experiment (bpy 5.3 + Cycles CPU + Pillow 12.3, 4 cores); scripts and renders are in the session scratch dir `…/scratchpad/art-exp` (not in the repo — `lib.py`, `post.py`, `exp3.py`, `comp3.py` are ~250 lines and can be ported to `tools/art/` as the seed of the real pipeline).

## 1. One-line style

A cold, charcoal-and-violet stone bureaucracy seen in 2:1 isometric pixel art, where the only warm things are window light, fire and paperwork — and the only saturated things are Heaven's gold (screen-left) and Hell's red (screen-right).

## 2. Palette — "Border-24" (exact, the only colours a shipped sprite may contain)

| Ramp | Hex (dark → light) | Use |
|---|---|---|
| Ink/charcoal/grey (violet-biased) | `#0d0b12` `#1a1722` `#27232f` `#37323f` `#4b4654` `#66616e` `#8a8591` `#b5b0b8` | outline, mortar, all stone, iron, paper |
| Muted purple | `#2a1f3d` `#43325c` `#6a5484` `#9a86ad` | ambient shadow, clerk robes, fog, soul outline |
| Gold light | `#6b4a1e` `#a8742a` `#e0a83e` `#f6d67a` `#fff3c4` | windows, flame core, Heaven, trim, UI accent |
| Infernal red | `#3a0f14` `#74161b` `#b3261e` `#e8552b` | banners, carpet, Hell, guard hems, flame edge |
| Wood | `#5a3f2e` | desks, shelves, doors (shade with `#27232f`, light with `#a8742a`) |
| Soul | `#cfe0e6` `#8fa3b3` | souls only — the one cool-cyan note in the game |

Rules: stone never uses pure neutral grey (always the violet-biased ramp). Gold and red together may not exceed ~15 % of any Purgatory screen. `#fff3c4`, `#f6d67a`, `#e8552b` are **emissive-only** indices (see §7). `#cfe0e6/#8fa3b3` are reserved for souls so a soul is identifiable by colour alone at 10 px.
Known gap ✔: gold light falling on grey stone has no in-palette warm mid-tone (my lighting test re-quantised lit stone to lilac). Either accept off-palette blends from Godot lights (recommended) or add one bridge colour (`#7a6450`) if lighting is ever baked.

## 3. Lighting rules

1. **Ambient is cold.** Scene tint ≈ `#9e94cc` multiply (CanvasModulate) — everything unlit drifts to violet-charcoal.
2. **Light is warm and local.** Gold pools only from windows, braziers, candles, the statue's lantern. Pools are *banded* (4–5 flat steps, no smooth gradient ✔ reads as pixel art) and elliptical 2:1 on floors.
3. **Baked form shading is fixed and directional:** top faces lightest, left-facing (−Y) faces mid, right-facing (+X) faces darkest. One sun (warm white) + one weak violet fill, identical for every asset, so any module fits any room.
4. **Emissive never dims.** Window glass/flames sit on an unlit layer so the ambient tint cannot grey them (✔ in my first composite the multiply turned windows lilac; masking emissive indices fixed it).
5. **Geography is colour:** the closer to the Heaven side (screen-left / west), the more gold window light and pale `#b5b0b8` trim; toward the Hell side (right / east), more red banners, ember-orange light, `#3a0f14` shadow. Centre (Judgement, statue court) is balanced — both lights meet on the statue.
6. No baked cast shadows on sprites. Characters/props get a 2:1 ink ellipse at ~45 % alpha (✔ sufficient grounding).

**Heaven side:** inverted values — light `#f6d67a/#fff3c4` masses, `#e0a83e` shadow, thin tall lancets, cloud banks in `#9a86ad/#b5b0b8`, vertical god-ray bands. Overbright and slightly bleached: beautiful but hard to look at. **Hell side:** near-silhouette `#1a1722/#3a0f14` towers, lava slits in `#e8552b`, heavy squat buttresses, chains, smoke bands in `#74161b`. **Purgatory:** the only place with mid-greys — literally the grey area.

## 4. Isometric convention (recommended)

| Item | Value |
|---|---|
| Projection | Dimetric "2:1 iso". Orthographic camera `rotation_euler = (60°, 0°, 45°)` (30° elevation) ✔ gives exact 2:1 diamond |
| World unit | 1 Blender unit = 1 tile |
| Tile footprint | **64 × 32 px** diamond (`ortho_scale = max(W,H) / 45.2548`) ✔ tiles butt seamlessly |
| Vertical scale | 39.19 px per unit of height; wall storey = **96 px** (2.449 u); half-wall/rail = 24 px; stair step = 8 px (4 steps/tile = 32 px rise) |
| Character | ~**36 px** tall (0.86 u incl. hood), 16–18 px wide, cell **32 × 56**, feet anchor at (16, 48) |
| Grid → screen | `sx = (x+y)*32`, `sy = (x−y)*16`; draw order by `(x−y)`, i.e. Godot Y-sort on feet anchor |
| Pixel density | 1 art px = 1 texel; integer scaling only; suggested base viewport **640 × 360** (≈10 tiles across; TA/UI to confirm). Nearest filtering, no mipmaps |
| Directions | Axes: +X = screen down-right (SE), +Y = up-right (NE). Dir index 0..7 = facing rotated 45°·i from "toward camera-left (SW)" |

Why 64×32/36 px: at 640×360 a clerk is ~1/10 screen height — small enough for "hundreds of small characters", large enough that hood, hem colour and a carried book survive (✔ readable in tests). The wide fortress vista of the concept mock-up is a *map/backdrop* view, not gameplay zoom (see Risks).

## 5. Fortress architecture kit (modular, all on the 1-unit grid)

Wall modules occupy the far 1/4 of a tile (0.25 u thick) and come in two orientations: `_x` (runs along X, shows lit left face) and `_y` (runs along Y, shows dark right face). Rendered separately, never mirrored (mirroring breaks rule 3).

- **Floors:** flagstone (4 slabs/tile, mortar `#27232f`) ✔; flat 64×32 diamond for interiors, 64×48 "edge" variant with 10 px skirt for platform edges ✔; variants: worn path, red-carpet runner, inlaid gold seam (queue guide), grate, cracked.
- **Walls:** plain; lancet-window (pointed equilateral arch, mullion + transom, emissive glass) ✔; door arch; low parapet with crenels; corner pier. Plinth, string course at 0.5 u, cornice cap in `#8a8591` (the cap is essential ✔ — hides texture streaks on wall tops and gives the pixel-art "lit top edge").
- **Brick rule ✔:** course height exactly 6 px (`6/39.19` u), brick 12 px, mortar ≥ 1 px (0.031 u). Sub-pixel or unaligned mortar aliases into noise under point sampling.
- **Vertical gothic set:** flying buttress (2 tiles), pier buttress with pinnacle, spire cap (1×1 and 2×2), tracery rose (2-tile wall), gargoyle bracket, clustered column.
- **Circulation:** stairs (1 tile, 4 steps, both axes), grand stair (3 wide), bridge deck + pointed-arch span below (2/3/4 tiles), balustrade.
- **Dressing:** banner (red, fleur/scale sigil, 2-frame sway), brazier (4-frame flame) ✔, wall torch, candle stand, clerk desk with papers + candle ✔, lectern, bookshelf (1 tile, 96 px), ledger stack, filing cart, queue rail + post, ticket booth, bench, stamp plinth, hooded-angel statue with staff/lantern (2×2 tiles, 160 px tall) on stepped base with gold inlay ring.

## 6. Characters

All are one parametric rig (tapered robe cone, head, hood cone, two arm stubs, optional prop) so silhouettes differ by **hood shape, hem colour and prop**, which is what survives at 36 px ✔.

| Character | Read at a glance | Palette |
|---|---|---|
| Player clerk | pointed hood, **gold hem**, carries pale ledger; faint gold selection ring at feet | robe `#43325c`, hem `#e0a83e`, ledger `#b5b0b8` |
| Hooded clerks (NPC) | same body, grey hem, no ring; rank = hem (grey → lilac → gold thread) | robe `#37323f`/`#43325c` |
| Souls | no hood, no face, no feet (robe fades), 1 px lilac outline instead of ink, drawn at 75 % alpha + 1 px vertical bob ✔ | `#cfe0e6` / `#8fa3b3`, outline `#6a5484` |
| Guards | charcoal robe, **red hem**, tall spear with gold tip (breaks the 36 px line, visible in crowds) ✔ | `#27232f`, `#b3261e` |
| Archivist | hunched (shorter, 30 px), huge book stack on back, candle on head-band (tiny emissive) | `#5a3f2e`, `#f6d67a` |
| Angel envoy | taller (44 px), no hood, flat halo disc, two blade-like wing planes; emits gold | `#b5b0b8`, `#f6d67a`, `#fff3c4` |
| Demon envoy | taller (44 px), horned cowl, wide shoulders, ember eyes (2 emissive px), formal red sash | `#1a1722`, `#74161b`, `#e8552b` |

**Animation:** 8 directions rendered (cost is negligible ✔). Walk = 4 frames (bob + arm swing, 8 fps); idle = 2 frames (breathing, 2 fps); souls: float = 4 frames; work-at-desk = 2 frames (4 dirs only); guards add `attention` 1 frame. Envoys: walk 4 + talk 2. Sheet layout: **columns = direction 0..7, rows = frame**, cell 32×56 → walk sheet 256×224 ✔. One PNG per (character, animation) plus a generated `.json` (cell size, anchor, fps) for the Godot importer.

## 7. Art pipeline (recommended; validated end-to-end on a small kit)

```
tools/art/kit/*.py (bpy geometry builders)  →  Cycles low-res RGBA  →  post.py (alpha cut, palette map,
outline, emissive mask, sheet pack)  →  game/assets/**.png + .json  (committed, regenerable by `make art`)
```

**7.1 Scene construction.** Pure `bpy`/`bmesh` from `read_factory_settings(use_empty=True)`: boxes, cones, UV spheres, an extruded pointed-arch profile, boolean DIFFERENCE (EXACT) for window openings ✔. Materials are Principled BSDF with roughness 1, specular 0, flat palette colours (hex → linear). Stone uses a `Brick Texture` node driven by world Position (floors: x,y; walls: x+y,z so both wall orientations share one material) ✔. No image textures, no .blend files in the repo.

**7.2 Render settings that worked ✔**

| Setting | Value |
|---|---|
| Engine / device | `CYCLES`, CPU, `threads=4`, `use_persistent_data=True` |
| Samples | **64** (16 works but leaves 1-px gold speckle near emissive glass); adaptive sampling off; **denoise off** |
| Pixel filter | **`GAUSSIAN`, `filter_width = 0.01`** → true point sampling; alpha comes out binary (0/255). `BOX` ignores width and yields 13 alpha levels and soft brick edges — rejected |
| Resolution | final pixel size directly (64×32, 64×128, 32×56 …), 100 %; no supersample-and-downscale |
| Film | `film_transparent = True`, PNG RGBA 8-bit |
| Colour management | view transform **Standard**, look None (Filmic/AgX desaturate golds and break the palette mapping) |
| Bounces | `max_bounces = 2` |
| Lights | key sun 4.5 W/m², colour (1.0, .95, .88), direction (0.45, 0.8, −1.3), angle 0.02; fill sun 0.6, (.55, .45, .9), direction (−0.9, −0.2, −0.6); world (.42, .36, .62) × 0.55 |
| Emission | glass: emission strength 1.6 (rim) / 3.0 (core); flame 3–4. Clips cleanly to the gold ramp under Standard |
| Framing | camera aimed so the tile-centre lands on a fixed anchor pixel (walls: (32, H−16); characters: (16, 48)) |

**Timing ✔ (whole kit: 2 floors, 4 walls, brazier, desk, 3 characters × 8 dirs × 4 frames = 104 sprites):** 1.8 s wall-clock at 16 spp, **3.1 s at 64 spp**, including scene rebuilds. Per render at 64 spp: wall 64×128 ≈ 0.12 s, floor ≈ 0.03 s, character frame ≈ 0.016 s. Post-process is negligible. 104 PNGs = 66 KB. A full prototype rebuild should stay under ~30 s, so **CI can regenerate all art and diff it**.

**7.3 Post-process (`post.py`, numpy + Pillow) ✔**
1. Alpha: threshold at 128 → binary (already binary with the Gaussian-0.01 filter; threshold is a safety net).
2. Palette map: nearest Border-24 colour, luma-weighted RGB distance. **No dithering on sprites/tiles** (4×4 Bayer was tested and turns 64 px tiles to noise). Ordered Bayer dithering **only** on large backdrops, where it works well.
3. Outline: 1 px outer outline, 4-neighbour, `#0d0b12`, for characters and free-standing props (leave ≥1 px canvas margin). **No outline on floors/walls** (they must tile). Souls use `#6a5484`.
4. Emissive mask: pixels in the emissive indices are written to a sibling `*_e.png` (or flagged in the JSON) so Godot draws them unshaded/additive above the CanvasModulate tint.
5. Pack frames into sheets; write JSON metadata; fail the build if any pixel is off-palette or any sprite touches its canvas edge unexpectedly.

**7.4 Shadows & light in engine (recommendation to TA).** Baked: form shading only. Runtime: blob shadow sprite per actor; `CanvasModulate` cold tint; banded radial light textures (generated by Pillow, 5 steps, 2:1 ellipse) as `PointLight2D` or additive sprites — whichever is cheaper on the mobile Compatibility renderer. Flames/windows flicker by swapping 2–4 light-texture frames, not by scaling.

**7.5 Backdrops.** Heaven/Hell skies and distant skylines are procedural Pillow paintings (gradients + banded cloud noise + layered spire silhouettes with lit slits), quantised with Bayer dither ✔ (480×270 in 0.2 s). First test proves the method but is crude — skyline silhouettes should be rendered from the same Blender kit (spires, buttresses) at 1/4 scale and composited, for architectural consistency.

**Verdict from looking at the renders:** a 6×6 room assembled purely from the generated sprites (lancet-window walls on two sides, flagstones, braziers, desk, clerks, guards, a soul) reads immediately as dark gothic isometric pixel art with coherent light, and tiles/walls align with zero seams. Weakest element: characters are still "chess-piece" simple — acceptable at 36 px, but they need the prop/hood differentiation in §6 and a second pass.

## 8. Environmental storytelling

- **Arrival Hall:** switch-back queue rails worn into the floor (worn-path tile); ticket booth with an unreachable "NOW SERVING" counter; hundreds of unclaimed number-slips in the floor cracks; one bench where a soul has clearly waited so long it has ivy. West windows gold, east windows red — souls unconsciously queue toward one side.
- **Judgement office:** player desk small, near the door, under the dimmest window; superior's desk on a 1-step dais. Two outbound doors: gold-lit arch and red-lit arch, each with a differently worn threshold. In-tray visibly grows with backlog (3 states). A stamp plinth with gold and red wax.
- **Records annexe:** shelves taller than walls elsewhere (2 storeys), ladders, chained ledgers, a collapsed aisle roped off since "forever", candle stubs layered like stalagmites; one shelf conspicuously empty (story hook for Narrative).
- **Statue courtyard:** hooded angel with lantern, face worn off by touch; gold inlay ring in the paving, half of it scorched; banners from both powers hang on opposite parapets and are never quite the same length. Bridges visibly lead toward each realm.
- **Progress changes art:** repaired tiles, more braziers lit, extra desks staffed, banners swapped as faction favour shifts — all are tile/prop swaps, no new art technology.

## 9. Prototype asset list (exact)

Paths under `game/assets/` (TA may rename root). Sizes W×H px; "frames" = dirs × frames.

| # | File | Size (cell) | Frames |
|---|---|---|---|
| 1 | `tiles/floor_flag.png` (flat) | 64×32 | 4 variants (strip 256×32) |
| 2 | `tiles/floor_flag_edge.png` (skirt) | 64×48 | 2 (SE-edge, SW-edge) |
| 3 | `tiles/floor_carpet_red.png` | 64×32 | 3 (straight x, straight y, end) |
| 4 | `tiles/floor_goldseam.png` (queue guide) | 64×32 | 2 |
| 5 | `walls/wall_plain_{x,y}.png` | 64×128 | 1 each |
| 6 | `walls/wall_window_{x,y}.png` + `_e.png` | 64×128 | 1 each (+ red-glass variant for east rooms) |
| 7 | `walls/wall_door_{x,y}.png` | 64×128 | 2 each (closed/open) |
| 8 | `walls/wall_corner.png`, `walls/parapet_{x,y}.png` | 64×128, 64×64 | 1 each |
| 9 | `arch/buttress_pier.png`, `arch/spire_small.png` | 64×160, 64×192 | 1 each |
| 10 | `arch/stairs_{x,y}.png` | 64×80 | 1 each |
| 11 | `arch/bridge_deck.png`, `arch/bridge_arch_under.png` | 64×48, 128×128 | 1 each |
| 12 | `props/brazier.png` + `_e.png` | 32×48 | 4 (flame) |
| 13 | `props/wall_torch_{x,y}.png` + `_e.png` | 32×48 | 4 |
| 14 | `props/banner_red.png` | 32×96 | 2 (sway) |
| 15 | `props/desk_clerk.png` | 64×64 | 3 (in-tray empty/half/overflowing) |
| 16 | `props/desk_superior.png`, `props/lectern.png`, `props/stamp_plinth.png` | 96×80, 32×64, 32×48 | 1 each |
| 17 | `props/shelf_books_{x,y}.png`, `props/shelf_tall_{x,y}.png` | 64×128, 64×192 | 2 variants each (one "empty") |
| 18 | `props/ledger_stack.png`, `props/ladder.png`, `props/filing_cart.png` | 32×48, 32×112, 64×64 | 1 each |
| 19 | `props/queue_rail_{x,y}.png`, `props/queue_post.png`, `props/bench.png` | 64×48, 16×32, 64×48 | 1 each |
| 20 | `props/ticket_booth.png` + `_e.png` | 64×112 | 1 |
| 21 | `props/statue_angel.png` + `_e.png` (2×2 tiles) | 128×192 | 1 |
| 22 | `props/statue_base_inlay.png` (floor decal, 4×4 tiles) | 256×128 | 1 |
| 23 | `chars/player_{idle,walk}.png` | 32×56 | 8×2, 8×4 |
| 24 | `chars/clerk_{idle,walk,work}.png` (3 hem tints via palette swap) | 32×56 | 8×2, 8×4, 4×2 |
| 25 | `chars/soul_{idle,float}.png` (4 body variants: build/height) | 32×56 | 8×2, 8×4 |
| 26 | `chars/guard_{idle,walk}.png` | 32×64 | 8×2, 8×4 |
| 27 | `chars/archivist_{idle,walk}.png` | 32×56 | 8×2, 8×4 |
| 28 | `chars/angel_envoy_{idle,walk}.png`, `chars/demon_envoy_{idle,walk}.png` (+ `_e`) | 48×72 | 8×2, 8×4 |
| 29 | `fx/shadow_blob.png`, `fx/select_ring.png` | 32×16 | 1, 4 |
| 30 | `fx/light_pool_{gold,red}.png` (banded) | 192×96 | 2 (flicker) |
| 31 | `fx/soul_wisp.png`, `fx/dust_mote.png` | 8×8 | 4 each |
| 32 | `bg/heaven_sky.png`, `bg/heaven_skyline.png`, `bg/heaven_clouds.png` | 640×360, 960×240, 960×160 | 1 each (3 parallax layers) |
| 33 | `bg/hell_sky.png`, `bg/hell_skyline.png`, `bg/hell_smoke.png` | 640×360, 960×240, 960×160 | 1 each |
| 34 | `bg/void_fog.png` (purple, tileable, under bridges) | 256×128 | 2 (drift) |

≈ 34 asset families, ~75 PNGs, estimated < 1 MB total and < 30 s to regenerate.

## 10. Dependencies on other roles

- **Technical Architect:** confirm tile 64×32, base viewport (640×360 proposed), integer scaling, Y-sort + anchor convention, TileMapLayer vs sprite scenes for walls, how `_e.png` emissive layers and banded lights are implemented on the Compatibility renderer, asset root path, JSON metadata schema, and whether generated PNGs are committed or built in CI.
- **Game Director:** movement model (8-way free vs grid) fixes how many directions matter; camera zoom levels; whether wall cut-away/fade is needed when the player walks behind walls (affects wall module height and a "low wall" variant set).
- **Narrative:** canonical sigils for Heaven/Hell/Purgatory banners, the statue's identity, named NPCs that need a unique silhouette; approval of §8 hooks (empty shelf, scorched ring).
- **UI/UX:** shares Border-24 (gold = interactable/accent, red = warning); needs icon set and portrait treatment — are soul portraits in the judgement UI generated by this pipeline (a larger 96×96 bust render) or abstracted?
- **Management/Sim:** which states must be visible in-world (backlog pile levels, staffed/unstaffed desk, morale?) so I can budget variant frames; crowd counts per room (drives soul variant count).
- **QA/Producer:** palette-lint and regenerate-and-diff should be part of the build checks.

## 11. Open questions / risks

1. **Character charm (highest art risk).** Procedural primitives give readable but generic "chess-piece" figures. Mitigation: silhouette props, hem colour coding, hand-tuned per-pixel touch-ups expressed as code (e.g. forced 2-px eye glints), and keeping characters small. A portrait system for dialogue would need its own investigation.
2. **Concept mock-up vs gameplay zoom.** The mock-up shows a whole district at once with ~12 px figures; that is not playable on a phone. I propose the gameplay camera in §4 and treating the vista as the Map screen/backdrop render. Needs Director + UI agreement.
3. **Occlusion.** Tall walls on the near side of rooms hide the player. Options: omit near walls (dollhouse cut, as in my test room), low 24 px near-walls, or fade. Unvalidated in Godot.
4. **Runtime lights leave the palette** (and cost fill-rate on mobile). Baked light pools per room are the fallback; needs a TA measurement.
5. **Gothic richness** (tracery, gargoyles, flying buttresses) is described but only the lancet window, plinth/cornice wall, brazier and desk were actually built. Boolean-heavy pieces may need more care; curved/diagonal modules (round towers, 45° bridges) are deliberately out of the prototype.
6. **Texture aliasing** under point sampling requires every pattern to be pixel-grid-aligned (§5 brick rule) — a discipline every new module must follow; add a lint render at 4× to catch it.
7. Not yet validated: import into Godot 4.6, Y-sorting of 0.25 u-thick walls against actors, animation feel of the 4-frame walk, the angel/demon/archivist rigs, and red-glass windows.
8. Determinism: Cycles noise seed is fixed, but cross-version Blender output may differ by a few pixels — pin the bpy version if art is diffed in CI.
