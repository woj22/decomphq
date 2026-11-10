# 04 — Technical Architecture & Common Standards

Owner: Technical Architect. Everything marked **STANDARD** is binding on other roles unless the cross-review changes it.
Experiment evidence: a throwaway Godot 4.6 project (run under `xvfb-run`, opengl3) confirmed the items marked *(verified)*.

## 1. Rendering approach — **2D isometric, pre-rendered sprites**

**Decision: pure 2D.** `TileMapLayer` (isometric, diamond-down) + Y-sort, with tiles/props/characters pre-rendered to pixel sprites by Blender (Cycles, orthographic) and/or procedural Python. No 3D nodes at runtime.

| Criterion | 2D pre-rendered (chosen) | 3D ortho + pixelation |
|---|---|---|
| Pixel-art fidelity | Exact: palette-quantised sprites, no shimmer | Texel crawl on camera motion, hard to make look hand-pixelled |
| Hundreds of characters, low-end phones | Batched quads; 400 sprites + map = **34 draw calls** *(verified)* | Skinned meshes or impostors, much higher GPU/CPU cost |
| Multi-level architecture | Needs conventions (§3) — solved with storey bands *(verified)* | Free |
| Occlusion | Y-sort + storey bands; needs rules for tall objects | Free (depth buffer) |
| Lighting | Baked into sprites + additive glow sprites + `CanvasModulate` | Real-time lights too costly on Compatibility/low-end anyway |
| Automated assets | Blender renders 3D kits to sprites: 3D authoring convenience, 2D runtime | Same models, but also needs materials/LODs tuned for realtime |
| Testability here | Works on software GL, deterministic screenshots *(verified)* | Works but very slow under llvmpipe |

The cost of 2D (occlusion and elevation rules) is paid once in §3. The one thing we give up is camera rotation; the game has a fixed camera.

**Lighting STANDARD:** light is baked into sprites (emissive windows, torch glow rendered by Cycles). Runtime adds (a) one `CanvasModulate` per area for ambient tint (Heaven-side gold, Hell-side red, purgatory purple), (b) additive-blend "glow" sprites (flicker by animating `modulate.a`), (c) no `PointLight2D`/shadows in the prototype (max 4 hero lights later if profiling allows).

## 2. Renderer & display **STANDARD**

- Renderer: **Compatibility (GLES3)** on all platforms (`rendering_method` and `.mobile` override both `gl_compatibility`). Best 2D performance and device coverage; it is also the only renderer we can run in this container.
- Orientation: **landscape** (`sensor_landscape`). Base logical resolution **640×360**.
- Stretch: `mode=canvas_items`, `aspect=expand`, `scale_mode=integer`. *(verified: 1920×1080 window → exact 3× scale, visible rect 640×360.)* 720p→2×, 1080p→3×, 1440p→4×. Wider phones see more world (logical width 640–840); UI must anchor to edges and respect `DisplayServer.get_display_safe_area()`.
- Why `canvas_items` rather than `viewport`: world pixels stay integer-scaled and crisp while **fonts and UI vectors render at native device resolution** (readable text is essential for a reading-heavy game).
- Texture filter: project default **Nearest** (`default_texture_filter=0`), no mipmaps, `snap_2d_transforms_to_pixel=true`. Sprites imported lossless (no VRAM compression — they are tiny and compression ruins palettes).
- Camera zoom: integer only (1× default, 2× close-up). No fractional zoom; the "overview" is a Map UI screen, not a zoom-out.
- UI units are logical px at 640×360. Minimum touch target **40×40 logical px** (≈ 8 mm on a 6.3" 1080p phone). Body font ≥ 10 logical px (renders at 30 px on 1080p).

## 3. Isometric conventions **STANDARD**

**Grid.** 2:1 dimetric. Tile diamond **32×16 px**. Height unit `HU` = **8 px**. One storey = 6 HU = **48 px**. Characters: frame cell 24×40, visible figure ≈ 12×24, anchor at feet. Background souls 8×14.

**Transform** (matches `TileMapLayer.map_to_local`, *verified*): cell `(cx, cy)` centre →
`screen = ((cx − cy)·16 + 16, (cx + cy)·8 + 8)`. +x cell axis runs down-right (SE), +y runs down-left (SW). Inverse for continuous positions: `gx = sx/32 + sy/16`, `gy = sy/16 − sx/32` (after subtracting the (16,8) offset). All code uses `Iso.cell_to_world()` / `Iso.world_to_cell()` (static class `Iso`), never inline maths.

**Blender camera contract** (for the art pipeline): orthographic, rotation `(60°, 0°, 45°)` (elevation 30° → exact 2:1). 1 tile = 1 Blender unit; `ortho_scale = render_width_px / 22.627`. Vertical: 1 BU of Z = 19.6 px, so 1 HU = 0.408 BU, one storey = 2.449 BU. Render at final size with pixel-filter width ≈ 0.01 (no AA), then quantise to the shared palette and threshold alpha in Python (Pillow 12 and NumPy are installed).

**Elevation = storeys ("levels") + small heights.**
- A *level* `L` is a full storey. Each level has its own `TileMapLayer`s, drawn with `position.y = −L·48`, `y_sort_origin = L·48`, `z_index = L·10`. Entities on level L get `z_index = L·10`. So: upper storeys always draw over lower ones; Y-sort decides order inside a storey. *(Verified: character under a bridge is hidden by the deck, character on the bridge is visible, an upper-level wall in front of them occludes correctly.)*
- Consequence for art: **anything taller than one storey is sliced into 48 px storey segments**, each placed on its own level. A tower is a stack of tiles, not one tall sprite.
- Within a level, cells have a height `0..5` HU (stairs, daises). An entity's node position is always its **ground projection** on its level; height is applied as a sprite offset (`visual.position.y = −h·8`), so sorting is unaffected.
- Stairs between storeys: a run of stair cells with heights 0,2,4 on level L connecting to level L+1 height 0; the entity switches level (z_index) at the top cell.

**Y-sort rules.** One `World` node with `y_sort_enabled`; all level layers and the `Entities` node are Y-sorted children. Per level: `floor` layer is *not* sorted (`z_index = L·10 − 1`); `walls` and `props` layers are sorted with origin at the cell centre. Sprite sort point = feet/base-centre. Props wider than one cell are split per cell or restricted to 1×1 footprints in the prototype. Roofs/ceilings of interiors are not drawn (cutaway), walls on the two camera-facing sides are drawn as low (1 HU) kerbs so interiors stay visible.

**Collision & navigation.** No physics engine. Walkability is a grid: one `AStarGrid2D` per (area, level), `DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES`, built from the area JSON (200 path queries on 16×16 took 1.3 ms under software emulation). Levels are linked by explicit stair/door links (small graph on top; cross-level route = A* to link, then onward). A move between neighbours is legal if `|Δheight| ≤ 2` and Δheight ≠ 0 only on stair-flagged cells. NavigationServer is rejected: polygons are awkward to author as text, and grid A* is deterministic and trivially testable. Each cell has at most one walkable surface *per level*.

**Movement & input.**
- Entities hold `gpos: Vector2` (continuous cell coords) + `level: int`; screen position is derived. Player speed 3.5 cells/s.
- **Tap-to-move (primary):** tap → `canvas_transform.affine_inverse()` → world → for levels top-down, test `Iso.world_to_cell(world + (0, L·48))` for a floor → A* path → follow. Tapping an interactable paths to its `use_cell` and then triggers it.
- **Virtual joystick (secondary, left thumb):** stick vector is *screen-space* (up = up-screen). Converted with the inverse transform to a grid direction, normalised in grid space, then moved with slide-along-blocked-cells collision (circle radius 0.3 cells). Joystick input cancels any active path.
- Keyboard (WASD/arrows) maps to the same joystick vector for desktop testing. Actions: `move_*`, `interact`, `cancel`, `pause`.

## 4. Project layout **STANDARD**

```
/home/user/decomphq/
  game/                      # Godot project (res://)
    project.godot  export_presets.cfg
    autoload/                # one script per singleton (§4.1)
    core/                    # iso.gd, conditions.gd, effects.gd, rng.gd, json_util.gd
    world/                   # area_loader.gd, area.gd, tileset_builder.gd, camera_rig.gd
    actors/                  # actor.gd/.tscn, player.gd, npc_actor.gd, actor_pool.gd, crowd_layer.gd
    interact/                # interactable.gd, interaction_scanner.gd, door.gd, desk.gd
    sim/                     # agent_data.gd, schedule.gd, queue_zone.gd
    judgement/               # judgement_session.gd (logic), judgement_desk.tscn/.gd (screen)
    dialogue/                # dialogue_runner.gd
    ui/                      # hud/, dialogue_box/, judgement/, menus/, widgets/, theme/
    data/                    # ALL content (JSON): cases/ npcs/ dialogue/ areas/ ranks.json config.json
    assets/                  # GENERATED ONLY: tiles/ characters/ props/ ui/ fx/ audio/ fonts/
    tests/                   # run_tests.gd, unit/test_*.gd, playthroughs/*.json
  tools/                     # asset + content tooling, never shipped
    blender/                 # bpy scripts: render_tiles.py, render_characters.py, kits/
    procgen/                 # Pillow/NumPy generators: ui icons, fx, palette.py
    build_assets.py          # one entry point: regenerates game/assets/** deterministically
    validate_content.py      # JSON-schema check of game/data/**
    schemas/                 # *.schema.json (the formal version of §5)
    run_tests.sh  screenshot.sh
```

Rules: `assets/` is 100% reproducible from `tools/` (fixed seeds); generated PNGs **are committed** so the game runs without Blender. Each atlas ships a JSON manifest (`<name>.png` + `<name>.json`: per sprite `id`, `rect`, `origin`, `kind`, `solid`, `height_hu`, animations). `TilesetBuilder` builds the Godot `TileSet`/`SpriteFrames` from manifests at load — **no editor-authored resources**. Scenes (`.tscn`) are kept minimal and hand-writable; node trees of any complexity are built in code.

Naming: files/folders `snake_case`; a scene and its script share a basename; `class_name PascalCase`; nodes `PascalCase`; constants `UPPER_SNAKE`; private members `_prefixed`; static typing everywhere (`untyped_declaration` warning = error). Content IDs are `snake_case` with type prefix: `case_`, `npc_`, `dlg_`, `area_`, `rank_`, `flag_`, `item_`.

### 4.1 Autoloads (in load order)

| Name | Responsibility |
|---|---|
| `EventBus` | Global signals only, no state. |
| `Content` | Loads and validates `data/**` at boot; read-only lookup (`Content.case(id)`, `.npc(id)`, `.dialogue(id)`, `.area(id)`, `.rank(n)`). |
| `GameState` | All mutable, saveable state: rank, stats, flags, case verdicts, unlocked areas, per-NPC state. Evaluates conditions and applies effects (§5.1). |
| `Clock` | Game day/time, pause, fixed sim tick (4 Hz) emitter. |
| `Sim` | Data-only agents for every NPC/soul in every area; schedules, queues, backlog counters. |
| `World` | Loads/unloads areas, owns the current `Area` node, player spawn, transitions, camera rig. |
| `Dialogue` | Runs dialogue trees; emits lines/choices for the UI; applies effects. |
| `SaveGame` | Serialise/restore `GameState` + `Clock` + `Sim`; versioned migration; autosave. |
| `Audio` | Music/ambience crossfade per area, SFX pool, bus volumes. |
| `Playtest` | Only active with `--playtest=`; scripted input, assertions, screenshots (§8). |

**Signal conventions.** Local signals for parent↔child; `EventBus` for cross-system. Names are past-tense `snake_case`, typed args, IDs not node refs: `area_entered(area_id)`, `interactable_focused(id)`, `interaction_started(id)`, `dialogue_started(dlg_id)`, `dialogue_ended(dlg_id)`, `case_opened(case_id)`, `evidence_revealed(case_id, evidence_id)`, `case_judged(case_id, verdict)`, `stat_changed(stat_id, value, delta)`, `flag_changed(flag_id, value)`, `rank_changed(rank)`, `objective_changed(objective_id)`, `clock_ticked(day, minutes)`, `game_saved()`. UI **listens** to `EventBus` and **calls** autoload methods; gameplay code never references UI nodes.

## 5. Data formats **STANDARD** (JSON, UTF-8, one object per file unless stated)

All files have `"id"` and may carry a free-form `"ext": {}` object for role-specific fields the engine ignores. Formal schemas live in `tools/schemas/`; `Content` rejects unknown `op`s and dangling IDs at boot (fail fast, also in tests). Player-facing strings are inline English under keys named `text`/`name`/`title` (extractable to translation CSV later).

### 5.1 Conditions and effects (shared mini-language)
```json
{"conditions": [{"op":"flag","id":"flag_met_archivist"}, {"op":"stat_gte","id":"merit","value":10},
                {"op":"rank_gte","value":2}, {"op":"verdict","case":"case_miller","value":"heaven"},
                {"op":"any","of":[ ... ]}, {"op":"not","of":{ ... }}],
 "effects":    [{"op":"set_flag","id":"flag_x","value":true}, {"op":"add_stat","id":"merit","value":5},
                {"op":"unlock_area","id":"area_records"}, {"op":"queue_case","id":"case_miller"},
                {"op":"reveal_evidence","case":"case_miller","id":"ev_letter"},
                {"op":"start_dialogue","id":"dlg_x"}, {"op":"set_objective","id":"obj_first_shift"}]}
```
A `conditions` array is AND. New ops are added in `core/conditions.gd` / `core/effects.gd` only (one small function each) — the only code change content authors can ever trigger.

### 5.2 Soul case — `data/cases/case_<name>.json`
```json
{"id":"case_miller", "name":"Tobias Miller", "born":1871, "died":1923, "cause":"Drowned",
 "portrait":{"seed":4411, "tags":["male","old","worker"]},
 "summary":"A miller who fed a village through famine — with stolen grain.",
 "min_rank":1, "difficulty":1,
 "evidence":[
   {"id":"ev_ledger","source":"file","text":"Gave bread to 40 families, winter 1899.","weight":2,"tags":["charity"]},
   {"id":"ev_theft","source":"records","text":"Grain was taken from the abbey store.","weight":-2,
    "hidden":true,"contradicts":"ev_ledger"},
   {"id":"ev_confess","source":"interview","text":"\"I'd do it again.\"","weight":0,"hidden":true}],
 "interview":"dlg_case_miller",
 "verdicts":{
   "heaven":{"text":"He leaves through the gold door.","effects":[{"op":"add_stat","id":"heaven_favour","value":1}]},
   "hell":  {"text":"He does not argue.","effects":[{"op":"add_stat","id":"hell_favour","value":1}]}},
 "ext":{}}
```
`source` ∈ `file` (visible on the desk), `records` (revealed by consulting the Records Dept), `interview` (revealed by dialogue effect). `weight` (−3..+3) is advisory data for scoring/audits; no verdict is hard-coded "correct". Verdict keys are open (`heaven`, `hell`, later `defer`, `appeal`).

### 5.3 NPC — `data/npcs/npc_<name>.json`, dialogue — `data/dialogue/dlg_<name>.json`
```json
{"id":"npc_archivist_wren", "name":"Archivist Wren", "role":"archivist",
 "sprite":"clerk_f_01", "tint":"#9a8fb5",
 "home":{"area":"area_records","cell":[6,4],"level":0,"facing":"sw"},
 "schedule":[{"from":"08:00","to":"17:00","activity":"work","area":"area_records","cell":[6,4]},
             {"from":"17:00","to":"08:00","activity":"wander","area":"area_courtyard","zone":"zone_cloister"}],
 "dialogue":[{"id":"dlg_wren_intro","conditions":[{"op":"not","of":{"op":"flag","id":"flag_met_wren"}}]},
             {"id":"dlg_wren_default"}],
 "ext":{"morale":0.7,"competence":0.8,"secret":"..."}}
```
```json
{"id":"dlg_wren_intro", "start":"n1", "nodes":{
  "n1":{"speaker":"npc_archivist_wren","text":"You're the new clerk. Don't touch anything.","next":"n2"},
  "n2":{"speaker":"player","choices":[
     {"text":"I need a file.","next":"n3","conditions":[{"op":"flag","id":"flag_has_case"}]},
     {"text":"Sorry.","next":"end","effects":[{"op":"set_flag","id":"flag_met_wren","value":true}]}]},
  "n3":{"speaker":"npc_archivist_wren","text":"Third shelf.","next":"end",
        "effects":[{"op":"reveal_evidence","case":"$active_case","id":"$records"}]}}}
```
The first entry in `npc.dialogue` whose conditions pass is used. Node = `text`+`next`, or `choices`. `next:"end"` closes. `$active_case` resolves to the case on the player's desk.

### 5.4 Area (room/map) — `data/areas/area_<name>.json` — **ASCII-authored, no editor**
```json
{"id":"area_arrival_hall", "name":"The Arrival Hall", "size":[12,6], "ambient":"#8a7fa8", "music":"amb_hall",
 "legend":{".":"floor_flag", "#":"wall_stone", "=":"floor_carpet", "s":"stairs_ne", "D":"door_arch", " ":null,
           "t":"prop_torch", "d":"prop_desk"},
 "levels":[{"level":0,
   "floor": ["............","............","..========..","............","............","............"],
   "height":["000000000000","000000000000","000000000000","000000000000","000000000000","000000000000"],
   "walls": ["#####D######","#          #","#          #","#          #","#          #","############"],
   "props": ["            "," t   d    t ","            ","            ","            ","            "]}],
 "objects":[
   {"id":"door_to_court","type":"door","cell":[5,0],"level":0,"to":{"area":"area_courtyard","spawn":"from_hall"},
    "conditions":[]},
   {"id":"desk_player","type":"judgement_desk","cell":[5,1],"use_cell":[5,2]},
   {"id":"npc_slot_1","type":"npc_spawn","npc":"npc_receptionist_ada","cell":[2,3]}],
 "spawns":{"default":{"cell":[6,4],"level":0}, "from_court":{"cell":[5,1],"level":0}},
 "zones":{"zone_queue":{"kind":"queue","cells":[[3,3],[4,3],[5,3],[6,3]],"head":[6,3]},
          "zone_idle":{"kind":"wander","rect":[1,1,10,4]}}}
```
Row index = cell y, column = cell x; every row is exactly `size[0]` chars. Tile IDs in `legend` must exist in an atlas manifest; `solid`/`stairs` flags come from the manifest, so walkability is derived, never authored twice. `tools/` may generate areas procedurally; they diff cleanly in git. A `tools/preview_area.py` renders any area to PNG for review.

### 5.5 Ranks & progression — `data/ranks.json`; tunables — `data/config.json`
```json
{"stats":[{"id":"merit","name":"Merit","start":0}, {"id":"order","name":"Order","start":68,"min":0,"max":100},
          {"id":"coin","name":"Coin","start":0}],
 "ranks":[{"rank":1,"id":"rank_junior_clerk","title":"Junior Processing Clerk","requires":[],
           "on_reach":[{"op":"unlock_area","id":"area_arrival_hall"}]},
          {"rank":2,"id":"rank_senior_adjudicator","title":"Senior Adjudicator",
           "requires":[{"op":"stat_gte","id":"merit","value":30},{"op":"flag","id":"flag_first_audit_passed"}],
           "on_reach":[{"op":"unlock_area","id":"area_judgement_chambers"},{"op":"start_dialogue","id":"dlg_promotion_2"}]}]}
```
Stats are data-defined (the sim/director roles add theirs without code). `GameState` re-checks `requires` after every effect batch.

### 5.6 Save file — `user://save_<slot>.json`
```json
{"version":1, "saved_at":"2026-11-10T12:00:00Z", "playtime_s":812, "clock":{"day":3,"minutes":570},
 "player":{"area":"area_arrival_hall","cell":[6,4],"level":0},
 "rank":1, "stats":{"merit":12,"order":66,"coin":40}, "flags":{"flag_met_wren":true},
 "unlocked_areas":["area_arrival_hall","area_courtyard"],
 "cases":{"case_miller":{"state":"judged","verdict":"heaven","revealed":["ev_theft"],"day":2}},
 "case_queue":["case_okafor"], "objective":"obj_first_shift",
 "npcs":{"npc_archivist_wren":{"ext":{"morale":0.65}}}, "sim":{"rng_seed":991,"backlog":14}}
```
Only IDs and primitives — never node paths. Written atomically (`.tmp` then rename, previous kept as `.bak`). `SaveGame` runs `migrate_vN_to_vN+1` functions. Autosave on area change, verdict and app pause (`NOTIFICATION_APPLICATION_PAUSED`).

## 6. Core systems (prototype)

- **Player** (`actors/player.gd`): §3 movement; 4 facings (SE/SW/NE/NW), idle + 4-frame walk. Movement is locked while `Dialogue` or the desk is active.
- **Camera** (`world/camera_rig.gd`): `Camera2D` following the player with smoothing, clamped to area bounds, look-ahead 1 cell; cuts instantly on area change.
- **Interaction**: `Interactable` is a `Node2D` component (`id`, `prompt_text`, `use_cell`, `conditions`, signal `interacted(actor)`). `InteractionScanner` on the player picks the nearest enabled interactable within 1.5 cells each sim tick, emits `interactable_focused`, and the HUD shows one context button ("Talk", "Open", "Sit"). Tap on the object or the button both work.
- **Areas, not a streamed world.** The prototype is discrete areas (rooms and courtyards, ≤ 48×48 cells) joined by doors with a 0.25 s fade; load is synchronous from JSON (ms). The outdoor fortress view of the mockup is a later, larger area type; chunk streaming is deferred until an area exceeds budget. The *simulation* is already global (below), so the world stays alive off-screen.
- **Dialogue runner**: pure-logic state machine over §5.3; signals `line_shown(speaker_id, text)`, `choices_shown(Array)`, input via `Dialogue.advance()` / `Dialogue.choose(i)`. UI is a separate scene and can be replaced freely.
- **Judgement desk mode**: sitting at a `judgement_desk` pauses free movement and opens a full-screen UI scene driven by `JudgementSession` (logic only: current case, revealed evidence, notes, `call_soul()` → interview dialogue, `submit(verdict)`). Leaving the desk mid-case is allowed (to visit Records); the case stays open in `GameState`.
- **Progression**: verdict effects change stats → `GameState` checks the next rank's `requires` → `rank_changed` → `on_reach` effects (unlock areas, dialogue). Objectives are data (`set_objective`).
- **NPCs & simulation tick.** `Sim` owns a flat array of `AgentData` (id, kind, area, level, cell, target, path, state, schedule index) for *all* named NPCs and anonymous souls. `Clock` ticks `Sim` at **4 Hz**; agents are processed in round-robin buckets (≤ 64 per tick) so cost is constant. States: `idle`, `walk`, `work`, `queue`, `wander`. Queues are `queue_zone`s: agents hold a slot index and shuffle forward when the head is consumed (by a receptionist agent or by the player judging). Agents in unloaded areas advance abstractly (teleport on schedule change, queue counters only).
- **Presentation of agents**: the loaded `Area` binds agents to pooled `Actor` nodes (pool of 64, a `Sprite2D` + tiny script; position interpolated between ticks, animation frame set manually — no `AnimationPlayer` per NPC). Anonymous souls use a lighter `CrowdSprite` (single `Sprite2D`, 2-frame bob). Plain batched sprites are sufficient for the prototype *(400 sprites batched to ~30 draw calls)*. `MultiMeshInstance2D` is the later scaling step for 500+ crowds, with the caveat that a MultiMesh is one canvas item and cannot Y-interleave with walls — it would be split per queue zone/iso row band.

## 7. Performance budget & export

Target device: 2019-class low-end Android (2–3 GB RAM, Mali-G52 / Adreno 506, GLES 3.0).

| Budget | Value |
|---|---|
| Frame rate | 60 fps target, 30 fps hard floor (`max_fps` option 30 for battery) |
| Draw calls | ≤ 100 world, ≤ 150 total per frame |
| On-screen sprites | ≤ 600 (≤ 64 full actors, rest crowd sprites) |
| Atlases | ≤ **2048×2048** each; ≤ 4 loaded per area (tiles, props, characters, ui/fx) so batching holds |
| Texture memory | ≤ 64 MB; total process RAM ≤ 350 MB |
| Scripts per frame | ≤ 4 ms GDScript; sim only on the 4 Hz tick; no per-NPC `_process` |
| Area load | ≤ 300 ms; APK ≤ 80 MB |
| Overdraw | no full-screen alpha layers except one fog/vignette pass |

Rules: one material (default canvas item) for all world sprites; tint via `modulate` only; custom shaders need architect sign-off (they break batching). Fonts: one pixel-style TTF + one readable body TTF (generated or OFL-licensed).

**Android export needs:** Godot 4.6 export templates, Android SDK (platform-tools, build-tools 34+, cmdline-tools), JDK 17, a debug keystore, `export_presets.cfg` (arm64-v8a, min SDK 24, landscape, immersive mode), and `textures/vram_compression/import_etc2_astc=true`. **In this container:** Java and Gradle are present, but no export templates, no Android SDK, no device/emulator — so no APK and no on-device performance numbers. We commit `export_presets.cfg` and verify with touch emulation (`emulate_touch_from_mouse`) at 640×360/1280×720/2400×1080 windows. Software-GL fps here is not representative; we track draw calls and sprite counts instead. iOS needs a Mac + Xcode; nothing blocks it architecturally.

## 8. Testing (all automatable here)

1. **Content validation**: `python3 tools/validate_content.py` (JSON schema + cross-reference check: every ID, tile, sprite and dialogue target resolves; every area row has the right length; every door has a reciprocal spawn).
2. **Unit/logic tests (headless)**: `godot --headless --path game -s res://tests/run_tests.gd` discovers `tests/unit/test_*.gd` (methods `test_*`, simple `assert_eq` helpers, no third-party framework), prints a summary, exits non-zero on failure. Covers `Iso` round-trips, conditions/effects, dialogue traversal of *every* node, pathfinding reachability of every door/interactable in every area, every case completable with every verdict, save → load → save equality, rank progression from a scripted stat sequence.
3. **Scripted playthrough (rendered)**: `xvfb-run -a godot --path game --rendering-driver opengl3 --fixed-fps 60 -- --playtest=res://tests/playthroughs/prototype.json --out=<dir>`. Steps are JSON: `{"do":"tap_cell","cell":[5,2]}`, `{"do":"wait_signal","signal":"dialogue_started"}`, `{"do":"choose","index":0}`, `{"do":"press","action":"interact"}`, `{"do":"assert","conditions":[...]}`, `{"do":"screenshot","name":"desk"}`. `Playtest` injects real `InputEventScreenTouch` events through `Input.parse_input_event` (*verified*; note positions are **window** pixels, so the driver converts cell → world → canvas → window). Timeout per step → fail with screenshot.
4. **Screenshots**: `get_viewport().get_texture().get_image().save_png()` *(verified under xvfb at 1920×1080; fails under `--headless`, which has no renderer)*. `tools/screenshot.sh <area_id>` produces a per-area gallery for art/UI review; QA compares against the mockup by eye.
5. `tools/run_tests.sh` runs 1→3 in order; it is the definition of "green" for every task in §9.

## 9. Build plan (prototype) — S ≈ ½ day, M ≈ 1 day, L ≈ 2 days

| # | Task | Size | Depends |
|---|---|---|---|
| 1 | Project skeleton: `project.godot` (§2), autoload stubs, `Iso`, test runner, `run_tests.sh` | S | — |
| 2 | Schemas + `Content` loader + `validate_content.py` + one sample of each data type | M | 1 |
| 3 | Placeholder asset generator (procedural diamonds/blocks/figures + manifests) so code never waits for art | S | 1 |
| 4 | `TilesetBuilder` + `AreaLoader` (ASCII → levels, Y-sort, nav grids) + `preview_area.py` | L | 2,3 |
| 5 | Player: tap-to-move, joystick, collision, camera rig | M | 4 |
| 6 | `World` area transitions, doors, spawns; 3–4 linked areas | M | 5 |
| 7 | Interactable + scanner + HUD prompt | S | 5 |
| 8 | `GameState` conditions/effects, `Clock`, `EventBus` wiring, minimal HUD (location/day/stats/objective) | M | 2 |
| 9 | Dialogue runner + dialogue box UI | M | 7,8 |
| 10 | `Sim` agents, schedules, wander, queue zones, actor pool, crowd sprites | L | 6,8 |
| 11 | Judgement session + desk UI (file, evidence, interview, verdict) | L | 9 |
| 12 | Progression: ranks, unlocks, promotion beat; objectives | S | 11 |
| 13 | `SaveGame` + autosave + migration scaffold | S | 8 |
| 14 | `Playtest` driver + full prototype playthrough + screenshot gallery | M | 12 |
| 15 | Real art drop-in (Blender kits → atlases), glow sprites, ambient tint, audio stubs | L (art) | 4 |
| 16 | Perf pass (draw calls, sprite counts), Android preset, touch-size audit | S | 14,15 |

Tasks 1–3 unblock everyone; 8–9 and 4–7 can run in parallel; 15 runs alongside from task 4 onward.

## Dependencies on other roles

- **Art/Environment**: must adopt §3 exactly (32×16 tile, 8 px HU, 48 px storey slices, Blender camera contract, feet-anchored 24×40 character cells, 4 facings) and emit atlas + JSON manifest; shared palette file `tools/procgen/palette.py`. Needs to confirm the cutaway-interior rule and the storey-slicing rule are acceptable visually.
- **UI/UX**: design at 640×360 logical px, expand-aware anchoring to 840 wide, ≥ 40 px touch targets; screens are scenes listening to `EventBus`. Needs to confirm joystick vs tap-only and the judgement-desk layout so `JudgementSession`'s API covers it.
- **Narrative**: authors cases/NPCs/dialogue in §5 formats; tell me any needed construct that is missing (timed choices, multi-soul cases, appeals, verdicts beyond heaven/hell) so it becomes an `op` or field now.
- **Director/Systems**: canonical stat list, rank requirements, verdict consequence model (is there scoring/audit?), length of a "day".
- **Management/Sim**: which per-NPC and per-department variables exist (they go in `ext` → promoted to schema), required tick granularity, whether off-screen areas need more than abstract simulation.
- **QA/Producer**: owns `tests/playthroughs/*.json` and the definition of done; arbitration of any change to a STANDARD.

## Open questions / risks

1. **Zoom vs the mockup.** At 640×360 with 32×16 tiles, ~20 tiles span the screen — closer than the mockup's sweeping vista, chosen for phone readability and touch accuracy. The vista can be a pre-composed backdrop/Map screen. Needs director/art sign-off; halving sprites later is expensive.
2. **Y-sort edge cases**: multi-cell props, arches the player walks through, and characters straddling a storey change on stairs. Mitigation: 1×1 footprints, arches split into two pillar tiles + an upper-level lintel, level switch at the top stair cell. Verified only on a synthetic scene so far.
3. **Storey slicing** multiplies tile count and art-pipeline complexity for tall gothic architecture; purely decorative skyline (Heaven/Hell towers) should be non-interactive parallax backdrops instead.
4. **No device testing here**: performance budgets are unvalidated on real hardware; Android export toolchain is absent. First on-device build is a risk milestone that must happen outside this container.
5. **Cycles → pixel art quality**: quantised renders can look "pre-rendered 3D" rather than hand-pixelled. Art must prove the look on one tile kit + one character early (task 15 spike) before bulk generation.
6. **Text-authored scenes/UI** without the editor is slower for complex UI; code-built UI must stay disciplined (shared theme, widget helpers).
7. **GDScript sim scaling**: 4 Hz bucketed ticks should handle ~1–2k data agents, but unmeasured on a phone; fallback is coarser abstract simulation for off-screen areas.
8. **Integer scaling on unusual resolutions** (e.g. 1600×720 → 2×, 800×360 logical; tablets 4:3) changes the visible world area; UI must be tested at 16:9, 20:9 and 4:3.
