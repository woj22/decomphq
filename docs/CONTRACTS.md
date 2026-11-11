# Build Contracts — M1 prototype

Interfaces between the three parallel build workstreams. `PROJECT.md` is the spec; this file pins the seams so that
**Art** (`tools/` → `game/assets/`), **Content** (`game/data/`, `tools/validate_content.py`) and **Engine** (all other `game/` code)
can build at the same time without waiting on each other. If you must deviate, write it in `docs/CONTRACT_CHANGES.md`
(append: who, what, why) — never silently.

Ownership (do not write in another stream's directories):
- Art: `tools/blender/`, `tools/procgen/`, `tools/build_assets.py`, `tools/preview_area.py`, `game/assets/**`.
- Content: `game/data/**`, `tools/validate_content.py`, `tools/schemas/`.
- Engine: `game/project.godot`, `game/{autoload,core,world,actors,interact,sim,judgement,dialogue,ui,tests}/**`, `tools/run_tests.sh`,
  `tools/screenshot.sh`. Engine may put throwaway fixtures under `game/tests/fixtures/`.

## 1. Asset manifests (Art produces, Engine consumes)

Atlases live in `game/assets/<group>/<atlas>.png` with `<atlas>.json` beside it. Groups: `tiles`, `walls`, `props`, `characters`, `fx`,
`backdrops`, `ui`, `portraits`. Engine discovers atlases by scanning `res://assets/**.json`; sprite IDs are globally unique.

```json
{"atlas":"walls", "image":"walls.png", "sprites":{
  "floor_flag_0":   {"rect":[0,0,64,32],  "origin":[32,16], "kind":"floor"},
  "wall_plain_x":   {"rect":[64,0,64,128],"origin":[32,112],"kind":"wall", "solid":true},
  "brazier_0":      {"rect":[0,128,32,48],"origin":[16,40], "kind":"prop", "solid":true, "frames":4, "fps":6},
  "chr_clerk_grey": {"rect":[0,0,256,448],"origin":[16,48], "kind":"character", "cell":[32,56],
                     "dirs":["sw","w","nw","n","ne","e","se","s"],
                     "anims":{"idle":{"row":0,"frames":2,"fps":2},"walk":{"row":2,"frames":4,"fps":8},
                              "work":{"row":6,"frames":2,"fps":2}}}}}
```
- `origin` = the pixel that sits on the **centre of the cell at floor level** (floors/walls/props) or on the **feet** (characters).
  Engine places a sprite at `Iso.cell_to_local(cell) - origin`.
- Animated non-characters: `frames` laid out horizontally starting at `rect`, each `rect.w` wide (rect describes frame 0).
- Characters: frame (dir i, anim a, frame f) = `rect.x + i*cell.w`, `rect.y + (anims[a].row + f)*cell.h`. Column order = `dirs`.
- Optional keys: `solid` (default false), `height_hu`, `footprint` ([w,h] cells, default [1,1]), `additive` (true for light pools).
- Engine **must** fall back to a code-drawn placeholder (coloured diamond / block / capsule, labelled) for any missing ID, and log it once.

### 1.1 Required sprite IDs (Art must produce exactly these names; variants `_0.._n`)
Floors `floor_flag_0..3`, `floor_carpet_red_0..2`, `floor_goldseam_0..1`, `decal_inlay_ring` (256×128, origin = centre of its 4×4 footprint).
Walls (64×128 unless noted): `wall_plain_x`, `wall_plain_y`, `wall_window_gold_x`, `wall_window_gold_y`, `wall_window_red_x`,
`wall_window_red_y`, `wall_door_x`, `wall_door_y`, `wall_door_gilt_x`, `wall_door_gilt_y`, `wall_door_ember_x`, `wall_door_ember_y`,
`wall_corner`, `wall_kerb_x`, `wall_kerb_y` (64×48), `wall_kerb_corner`, `stairs_up` (64×80), `wall_plaque_x`, `works_hatch_y`.
Convention: `_x` = wall running along the cx axis (grid row 0, the far NE wall; its face looks toward screen bottom-left);
`_y` = wall along the cy axis (grid column 0, far NW wall; face looks toward screen bottom-right). `wall_corner` at (0,0).
Kerbs: last row → `wall_kerb_x`, last column → `wall_kerb_y`, last-row-last-column → `wall_kerb_corner`.
Props: `brazier_0` (animated), `wall_torch_x`, `wall_torch_y`, `banner_red`, `desk_clerk`, `desk_superior`, `dais`, `stool`, `bench`,
`bench_soul`, `lectern`, `shelf_books`, `shelf_empty`, `counter`, `rope_post`, `queue_rail_x`, `queue_post`, `ticket_booth`,
`statue_first_clerk` (footprint [2,2], origin on the centre of the 2×2 footprint), `ivy_bench`, `desk_registrar`.
Characters: `chr_player`, `chr_player_r2`, `chr_clerk_grey`, `chr_clerk_lilac`, `chr_archivist`, `chr_guard`, `chr_soul_0..3`.
Souls have only `idle` (4 frames, the float) and `walk`. Guard adds `attention` (1 frame).
FX: `shadow_blob`, `select_ring` (4 frames), `light_pool_gold`, `light_pool_red` (additive), `dust_mote` (4 frames), `tap_marker` (4 frames).
Backdrops (separate PNGs, no atlas packing needed but still with a manifest): `bg_heaven_sky`, `bg_heaven_skyline`, `bg_hell_sky`,
`bg_hell_skyline`, `bg_void_fog`.
UI (`ui` atlas, sizes from UI 05 §13 / PROJECT §10.9): `icon_map`, `icon_journal`, `icon_pause`, `icon_soul`, `icon_obol`, `icon_order`,
`icon_crest_r1`, `icon_crest_r2`, `pip_full`, `pip_empty`, `icon_link`, `icon_halo`, `icon_flame`, `stamp_heaven`, `stamp_hell`,
`stamp_rm0`, `icon_lamp`, `icon_key`, `icon_quill`, `btn_action` (64×64), `parchment_9` (9-slice, `"slice":[l,t,r,b]`), `panel_9`.
Portraits 64×64: `por_marrow`, `por_pell`, `por_wren`, `por_grist`, `por_registrar`, `por_works`, `por_soul`, `por_nan`, `por_oddy`.
Busts 96×96: `bust_case_s001_neutral|distressed|relieved` … for s001, s002, s003, s004, s007, s008.
Audio `game/assets/audio/*.wav` (synthesised): `sfx_tap`, `sfx_page`, `sfx_quill`, `sfx_door`, `sfx_stamp`, `sfx_bell`, `sfx_link`,
`amb_court`, `amb_hall`, `amb_records`, `amb_booths`, `amb_chamber` (loops, ≤ 8 s).
Fonts `game/assets/fonts/` + licence files (best effort; Engine falls back to the default font).

## 2. Areas (Content produces, Engine consumes) — `game/data/areas/area_*.json`
Single level for M1. The `grid` is **exactly** the ASCII in PROJECT §10.2 (row = cy, column = cx).
```json
{"id":"area_records_annexe", "name":"Records Annexe", "size":[10,8], "ambience":"amb_records",
 "backdrop":"none",                       // "court" = Gilt sky left + Ember sky right; "none" = void fog
 "grid":["##########","#SSSSSeSSk", "..."],
 "legend":{
   "#":{"kind":"wall"}, "k":{"kind":"kerb"}, "D":{"kind":"door"}, ".":{"kind":"floor"},
   "S":{"kind":"prop","prop":"shelf_books","solid":true}, "P":{"kind":"floor"}, "c":{"kind":"prop","prop":"counter","solid":true}},
 "floor":"floor_flag",                     // base floor family; Engine picks variant by hash(cx,cy)
 "windows":[{"cell":[3,0],"glass":"gold"}],// wall cells drawn with window sprites
 "decor":[{"sprite":"light_pool_gold","cell":[1,1]}, {"sprite":"wall_torch_x","cell":[4,0]}],
 "objects":[
   {"id":"door_records_court","type":"door","cell":[2,7],"style":"plain","to":{"area":"area_clerks_court","spawn":"from_records"}},
   {"id":"obj_pell_counter","type":"npc","npc":"npc_pell","cell":[5,3],"facing":"s","use_cell":[5,5]},
   {"id":"obj_empty_shelf","type":"inspect","cell":[6,1],"use_cell":[6,2],"dialogue":"dlg_empty_shelf"}],
 "spawns":{"default":[2,6], "from_court":[2,6]},
 "zones":{"zone_queue_1":{"kind":"queue","cells":[[1,2],[2,2]],"head":[8,2]}}}
```
- `kind` ∈ `wall, kerb, door, floor, prop, stair, queue, seat, decal`. Walls/kerbs/doors pick `_x/_y/corner` sprites from their position
  (§1.1 convention). `door` cells are walls in the grid; walkable only as the door's own cell; `style` ∈ `plain, gilt, ember`.
- Object `type` ∈ `door, npc, desk_player, inspect, hatch, stair, soul_door` (gilt/ember exits; souls only).
  `use_cell` = where the player stands to interact (default: nearest walkable neighbour).
- `decal_inlay_ring` and other decals: `{"sprite":..,"cell":..}` in `decor` (drawn under actors).

## 3. NPCs, dialogue, flow (Content produces, Engine runs)
- NPC `game/data/npcs/npc_*.json`: as 04 §5.3 (`id, name, title, sprite, portrait, dialogue[{id, conditions}]`, optional `wander`).
  First dialogue whose conditions pass is used.
- Dialogue `game/data/dialogue/dlg_*.json`: as 04 §5.3 node graph. Node keys: `speaker` (npc id | `player` | `narrator` | `$soul`),
  `text` (≤ 140 chars), `next` | `choices[{text, next, conditions, effects}]`, `effects`, `conditions` (node skipped to `else` if false).
- Flow triggers `game/data/triggers.json`: `[{"id", "on":"<EventBus signal>", "match":{argname:value}, "conditions":[], "effects":[], "once":true}]`.
  Signals usable in triggers: `area_entered(area_id)`, `case_scored(case_id)`, `case_called(case_id)`, `discovery_made(case_id, discovery_id)`,
  `dialogue_ended(dlg_id)`, `shift_started(day)`, `shift_ended(day)`, `new_game_started()`, `rank_changed(rank)`.
- Objectives `game/data/objectives.json`: `{"obj_id":{"text":"≤40 chars", "target":{"area":..,"object":..}}}`.
- Config `game/data/config.json` (every number in PROJECT §6/§10.6, incl. clock costs) and `game/data/ranks.json` (04 §5.5 shape,
  stats per PROJECT §8.5).
- Cases `game/data/cases/case_s00N.json`: PROJECT §8.5 **exactly** (s001, s002, s003, s004, s007, s008 for M1; s005, s006 too, `min_rank: 2`).
  Docket order lives in `config.json` → `"dockets":{"1":["case_s001","case_s002","case_s003"],"2":["case_s004","case_s007","case_s008"]}`.

### 3.1 Condition ops (Engine implements all; Content uses only these)
`flag{id}`, `not_flag{id}`, `stat_gte{id,value}`, `stat_lte{id,value}`, `rank_gte{value}`, `day_eq{value}`, `verdict{case,value}`,
`case_state{case,value}` (value ∈ `pending, called, seated, judged`), `discovered{case,id}`, `asked{case,id}`, `has_active_case{}`,
`active_case_eq{case}`, `docket_empty{}`, `holds_archive{case,id}`, `archive_available{}` (active case has un-held docs whose requires pass),
`any{of[]}`, `not{of}`.
### 3.2 Effect ops
`set_flag{id,value}`, `add_stat{id,value}`, `set_objective{id}`, `start_dialogue{id}`, `advance_clock{minutes}`,
`give_docket{day}` (loads `dockets[day]`), `start_shift{day}`, `end_shift{}` (opens the shift ledger), `call_soul{}` (next docket case:
spawn soul at the Registrar, it follows the player; Queue −1), `give_archive{}` (all available docs of the active case; +15 min if any),
`give_archive_one{case,id}`, `reopen_case{case}`, `snapshot_stats{tag}`, `restore_stats{tag}`, `reset_cases{ids[]}`,
`start_incident{id}`, `resolve_incident{id,resolved:bool}`, `unlock_area{id}`, `set_rank{value}` (plays the ceremony),
`show_card{title,text}`, `set_npc_line_flag{id}`, `buy_item{id,price}`, `teleport{area,spawn}`, `end_prototype{}`.
`$active_case` is valid wherever a `case` is expected.
