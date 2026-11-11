# The Purgatory Border — Project Document (single source of truth)

Version 1.0 · 2026-11-10 · Maintainer: QA/Producer (Agent 7)
Precedence: `DECISIONS.md` > `BRIEF.md` > **this document** > proposals `01`–`06`. The proposals are historical evidence;
where this document says "as 0N §x" that section is adopted verbatim, and where it gives a number, the number here wins.
The rulings behind every change are in `REVIEW.md` (IDs `C01`…).

---

## 1. Vision & pillars

**"You walk the paperwork."** A career RPG about a dead civil servant in the Border Chancery of Limen, the gothic fortress between
the Gilt side (Heaven, screen-left, gold) and the Ember side (Hell, screen-right, red). Every decision is made standing somewhere,
facing someone. Tone: dry bureaucratic satire on the surface, real moral weight underneath (02 §tone rule).

| Pillar | Test applied to every feature |
|---|---|
| P1 Places act, menus inform | "Where do I stand and who do I face to do this?" The bottom bar (Map / Journal / Pause, **D2**) is read-only. Staff, Reports and Upgrades are a roster board, a desk ledger and the Works Office. |
| P2 Judgement is reasoning, not guessing | A careful player can always explain why they lost Merit (§3). |
| P3 Rank changes the verbs | Rank N plays differently from rank N−1 within 5 minutes. |
| P4 The fortress remembers | Verdicts come back as people, notes and dialogue. |
| P5 Phone-shaped | Landscape (**D1**), one thumb, no real-time fail timers, stop mid-case and resume with no loss. |

## 2. Core loop

| Loop | Length | Steps |
|---|---|---|
| Minute | 30–90 s | Walk → talk/inspect → gain one fact → use it (link, ask, cite) |
| Case | 2–4 min | Call soul at Arrival Hall → (Records) → desk: read, link, ask → verdict + ground → soul exits by gold/red door → audit slip |
| Shift | 6–10 min | Docket from superior → 3 cases → one incident → report → shift ledger, pay |
| Career | 1–3 h per rank | Meet the rank gate → ceremony → new wing + new verb |
| Campaign | 12–15 h | Five acts = five ranks (§5) |

**Clock (ruling C07): action-driven.** Game time advances only when the player acts; it never runs while reading, deciding or idle.
Pressure comes from the Composure budget and from the queue growing with game time spent, never from a countdown.

| Action | Game minutes |
|---|---|
| Pass through a door / area transition | +5 |
| General question to a soul | +10 |
| Confrontation question (unlocked by a discovery) | +5 |
| Archive request at Pell's counter | +15 |
| Link (correct or wrong), reading, dialogue | 0 |
| Verdict stamped | +20 |

A shift starts at 08:00 when the superior hands over the docket and ends when the docket is done and the player reports back. Past 18:00
the HUD clock shows overtime; nothing fails. Animation and NPC walking run in real time (presentation only, §8.6).

## 3. Judgement system (owner: Director; content: Narrative)

### 3.1 Case anatomy
- **File**: registry summary + record entries `r1..rn`, each `tag` (virtue/sin/neutral) and `weight` −3..+3 (02 §6 conventions).
- **The Rubric** (02 §1): tally = sum of current weights; > 0 → Gilt Gate (Heaven), < 0 → Ember Gate (Hell), 0 → abstain (treated as ambiguous).
- **Archive documents** `arc_*`: obtained by walking to the Records Annexe and asking Pell. Some require a lead (`requires`).
- **Discoveries** `d_*`: each has one or more triggers and one or more ops:
  - `link: [entry, arc]` — the player selects that file entry and that archive card and taps LINK (for VOID / REWEIGHT);
  - `archive: arc_id` — revealed automatically when the document is received (for HIDDEN entries);
  - `question: q_id` — revealed by the soul's answer.
  - ops: `void entry` (weight → 0, struck through), `reweight entry → w`, `reveal hidden entry`.
- **Questions**: general (cost 1 Composure, +10 min) or confrontation (unlocked by a discovery or earlier answer; cost 0, +5 min). Max 4 visible.
- **Composure**: 3 pips at rank 1. General question −1; **wrong link −1**. At 0 the soul stops answering (ASK disabled); links still allowed at no further cost.
- **Facts** (the NOTES tab = the grounds list): every discovery yields one fact; a question may yield a fact. A fact's **side** is the sign of
  the tally change its ops cause (+ → Heaven, − → Hell); facts with no tally change carry an authored `side`.
  Up to 3 facts per case are marked `key` (the Diligence denominator).
- **Type** (authored, hidden): `clear` (file is true), `contested` (a discovery reverses or confirms against the surface reading), `ambiguous`
  (defensible both ways; 02 marks S-005/006/007).
- **Guideline verdict G** = Rubric applied to the **fully corrected record** (all discoveries applied) — 02's rule; ruling C05.

### 3.2 The unified scoring model (ruling C05)
**Sound** verdict: for `clear`/`contested` cases, verdict == G; for `ambiguous` cases (or G = abstain), **every verdict is sound**.
Audit labels: sound non-ambiguous = **Upheld**; unsound = **Overturned**; ambiguous = **Noted**.

**Merit per case = max(0, Diligence + Verdict + Grounds)**, range 0–9:
- **Diligence** = floor(3 × key facts found / key facts authored) → 0–3.
- **Verdict**: clear/contested: Upheld **+4**, Overturned **−2**. Ambiguous: **+4 if the cited ground's side == the verdict**, else 0.
- **Grounds**: the player cites **one discovered fact** (or "No ground"). **+2 if its side == the verdict**, else 0.
  Visible file entries cannot be cited (otherwise grounds are free).

Sound/Unsound feed Order and pay (§6). Merit feeds promotion (§4). Hidden, logged only: `favour_gilt`/`favour_ember` (+1 to the receiving side),
`conscience` (+1 Heaven-against-G or ambiguous Heaven, −1 the reverse). No right/wrong flash at the stamp: the audit slip arrives after the
soul has left (UI 05 §6.3 presentation + Director 01 §6.4 step 8).

### 3.3 Worked checks against the narrative cases (QA-computed; unit tests must reproduce)
Tallies re-verified for all eight 02 cases: filed/corrected S-001 +3/+3, S-002 +2/−4, S-003 −2/+1, S-004 −5/+1, S-005 0/−1,
S-006 +1/−1 (needs Q2 asked; scored on the authored −1), S-007 +5/+1, S-008 −4/+3. All match 02.

| Case (type, G) | Player behaviour | Key found | Verdict / ground | D + V + G = Merit | Sound |
|---|---|---|---|---|---|
| S-002 (contested, Hell) | Records, links r1↔arc_002a | 2/2 | Hell / d_two_ledgers (Hell) | 3 + 4 + 2 = **9** | yes |
| S-002 | Records, no link (arc_002b auto-reveals h1; known tally −1) | 1/2 | Hell / d_two_ledgers | 1 + 4 + 2 = **7** | yes |
| S-002 | Stamps the file as issued (+2) | 0/2 | Heaven / none | 0 − 2 + 0 → **0** | no |
| S-004 (contested, Heaven) | Both discoveries | 2/2 | Heaven / d_enemy_boy | 3 + 4 + 2 = **9** | yes |
| S-004 | Interview only (q2 reveals h1; known tally −2) | 1/2 | Hell / d_enemy_boy (Heaven) | 1 − 2 + 0 → **0** | no |
| S-004 | Interview only, follows conscience | 1/2 | Heaven / d_enemy_boy | 1 + 4 + 2 = **7** | yes |
| S-007 (ambiguous, +1) | All three discoveries | 3/3 | Heaven / d_widows (Heaven) | 3 + 4 + 2 = **9** | noted |
| S-007 | All three | 3/3 | Hell / d_kell (Hell) | 3 + 4 + 2 = **9** | noted |
| S-007 | All three, mismatched ground | 3/3 | Heaven / d_kell (Hell) | 3 + 0 + 0 = **3** | noted |
| S-007 | Never visits Records | 0/3 | Heaven / none | **0** | noted |
| S-008 (contested, Heaven) | All three | 3/3 | Heaven / d_violet_ink | **9** | yes |
| S-008 | Records, no links (arc_008c reveals h1; known −1) | 1/3 | Hell / none | 1 − 2 + 0 → **0** | no |

Result: following the file is punished only where the file is false; ambiguous cases reward reasoning on either side (P2 holds).

## 4. Progression & ranks
Ranks, new places and verbs: as 01 §4 table (titles from the BRIEF). Gates for ranks 2–5 are design intent until their milestone.
Act mapping as 02 §5. Rank is shown by the HUD crest, the player's cuffs (2-px arm detail: grey → gold-and-red) and NPC dialogue.

**Rank 1 → 2 gate (prototype, checked when S-008 is stamped):**

| Condition | Threshold |
|---|---|
| Cases processed | 6 / 6 |
| The violet-ink amendment found | `flag_found_violet_ink` (discovery `d_violet_ink` in S-008) |
| Merit | ≥ **30** of 54 |
| Overturned | ≤ **2** (of the 5 non-ambiguous cases) |

Outcomes: pass → promotion scene (02 §8). Violet ink missed → Pell lays the original on the desk, S-008 reopens as a **correction**
(its earlier Merit/Order/Overturned are reverted; arc_008a is already in the case) and re-stamping re-runs the check.
Merit/Overturned fail → "Docket reissued": shift 2 (S-004, S-007, S-008) resets; Merit and Overturned return to the end-of-shift-1 snapshot.
Reference totals (§10.8): perfect 54, attentive ≈43, half-diligent ≈31 (pass), Rubric-only without Records ≤16, careless ≈4 (fail).

## 5. World & narrative summary (owner: Narrative — full content in `proposals/02-narrative.md`)
Canonical names (use everywhere — code IDs, UI, docs):

| Thing | Name |
|---|---|
| Fortress / institution | Limen; the **Border Chancery** ("the Border", "the Keep") |
| Heaven / Hell | the **Gilt side** / **Ember side**; institutions **Auric Concord** (Bright Ministries) / **Cinder Dominion** (Pit Exchequer) |
| Exits for souls | **Gilt Gate** (gold door, screen-left) / **Ember Gate** (red door, screen-right) |
| God / Devil (never named in fiction) | the **Principal** / the **Counterparty**; off-stage until rank 4 |
| Guideline | **the Rubric** (replaces 01's "Codex") |
| Currency / % stat | **obols** (ob) / **Order** |
| Staff status | every employee, the player included, is a soul whose file is **DEFERRED** |
| Statue | **the First Clerk** (hooded, winged, lantern) in Clerk's Court |
| Antagonist apparatus | Auditor-General Corvin Thrace, Office of Reconciliation, **Room 0**, **violet ink** |

Factions (02 §2): Lustrants, Almoners, Choir of Accounts (Gilt); Wardens of Debt, Reclaimers, Furnace Guild (Ember); Proceduralists,
Discretionists, Residents (Chancery). Characters: 02 §4. Story "The Reconciliation", acts 1–5 = ranks 1–5 (02 §5): The Queue,
The Amendments, The Department, The Border, The Chair. Cases S-001…S-008: 02 §6 (S-005/S-006 are used from M2, §11).
Language rule: in-fiction text never uses "God", "the Devil", "angel", "demon" or real-faith terms (exception pending owner, REVIEW Q3).

## 6. Simulation & economy (owner: Management)
Full model (pipeline, efficiency, employees, economy, meters, expansion, tiers): as 06 §1–§10, **except**: the sim is advanced by
game minutes from the action clock (§2) rather than real seconds; "Build/upgrade" happens at the **Works Office** (D2; the Master Mason
staffs it); the "pocket ledger" lives in the **Journal**, not on the bar (D2). HUD coin = money the player controls (purse R1–2,
department budget R3, treasury R4–5; 06 §9). The mockup's 124 / 2,750 / 68 % are the 06 §5 fortress-wide Day-1 values (backlog,
treasury, Order) — the HUD of a rank-4+ player, not the prototype.

**Prototype subset** (all values in `data/config.json`):

| Counter | Rule |
|---|---|
| `queue_arrival` A | start 16; +3.0/game-h before 10:00, +2.0/game-h after; −1 when the player calls a docket soul |
| `queue_bench` J | start 8, cap 12; Registrar moves A→J at 2.4/game-h while A > 0 and J < 12 |
| NPC adjudicators | 2 desks remove 1.2/game-h total from J; the soul walks out the gold or red door (60/40 Hell-leaning, seeded) |
| **Queue** (HUD) | A + J; start 24. Fractions carry in accumulators; deterministic per seed |
| **Order** (HUD) | `clamp(68 + 2·Sound − 5·Unsound − max(0, Queue − 30) + 4·Resolved − 4·Unresolved, 0, 100)`; display eases 1 pt/s |
| **Obols** (HUD purse) | start 12; pay at each shift end: `8 + Processed + Sound − 2·Unsound + (3 if shift Accuracy ≥ 80 %)` |
| Sink | Works Office hatch sells one **desk lamp**, 20 ob: on later cases one not-yet-found link pair's file entry gets a parchment-white "lamp-lit" edge |
| Merit | §3.2; shown on the objective strip as "Merit n/30" |
| Day roll | no night step; counters carry over; next day starts 08:00 |

Example (attentive player, shift 1, 3 sound): pay 8+3+3+3 = 17 → purse 29; Order ≈ 68+6+4 = 78 before queue penalty.

## 7. Art standards (owner: Art; numbers ruled in C01–C04)

### 7.1 Palette "Border-24" — the only colours a world sprite may contain (03 §2)
| Ramp | Hex (dark → light) |
|---|---|
| Ink/stone (violet-biased) | `#0d0b12` `#1a1722` `#27232f` `#37323f` `#4b4654` `#66616e` `#8a8591` `#b5b0b8` |
| Muted purple | `#2a1f3d` `#43325c` `#6a5484` `#9a86ad` |
| Gold light | `#6b4a1e` `#a8742a` `#e0a83e` `#f6d67a` `#fff3c4` |
| Infernal red | `#3a0f14` `#74161b` `#b3261e` `#e8552b` |
| Wood | `#5a3f2e` |
| Soul (souls only) | `#cfe0e6` `#8fa3b3` |

Emissive-only: `#fff3c4` `#f6d67a` `#e8552b`. Gold+red ≤ ~15 % of a Purgatory screen. Lighting rules: 03 §3.
**Reserved:** saturated violet **`#8b3fd9`** is Room 0's ink — used only for amended record text and the RM 0 stamp, never in world sprites or other UI.

### 7.2 Grid, scale and camera (ruling C01) — Art's validated convention
| Item | Value |
|---|---|
| Projection | 2:1 dimetric; Blender ortho camera `rotation_euler = (60°, 0°, 45°)` |
| Tile | **64 × 32 px** diamond; 1 Blender unit = 1 tile |
| `ortho_scale` | **`max(W, H) / 45.2548`** (render size in px; Blender's scale spans the larger side) |
| Vertical | 1 BU of Z = **39.19 px**; height unit **HU = 16 px** (0.4083 BU); **storey = 6 HU = 96 px** (2.4495 BU) |
| Stairs | 4 steps × 8 px per stair cell = 2 HU per cell; 3 stair cells per storey |
| Near-side walls | **kerb 1 HU = 16 px** high (`wall_kerb_{x,y}`, 64×48); far walls full storey (64×128) |
| Character | ~**36 px** visible figure, 16–18 px wide; cell **32 × 56**, feet anchor (16, 48). Guard 32×64 (spear) |
| Facings | **8**; manifest stores `"dirs"` explicitly; canonical order (screen, clockwise): `sw, w, nw, n, ne, e, se, s` |
| Axes | Godot cell `(cx, cy)` ↔ Blender `(X, Y) = (cx, −cy)`: +cx = screen SE, +cy = screen SW (Blender +Y = NE) |
| Viewport | 640 × 360 base → ~10 tiles across (12.5 on 20:9). Integer scale only; nearest; no mipmaps |
| Zoom | 1× only in the prototype. The mockup vista is the **Map/backdrop** render, not the gameplay camera |

### 7.3 Sprite conventions
- One parametric character rig; identity by **hood shape, hem colour, prop** (03 §6 table). Player: pointed hood, **gold hem**, pale ledger, gold
  selection ring. NPC clerk rank by hem (grey R1 → lilac R2 → gold thread R3+). Souls: no hood, faceless in-world, `#6a5484` outline, 75 % alpha, 1-px bob.
- Animations: walk 4 frames @ 8 fps, idle 2 @ 2 fps, soul float 4, desk-work 2 frames × 4 dirs. Sheet: columns = direction, rows = frame.
- Outline 1 px `#0d0b12` (souls `#6a5484`) on characters/props only; never on floors/walls. No dithering on sprites; Bayer only on backdrops.
- Brick rule 03 §5 (6-px courses, 12-px bricks, ≥1-px mortar, grid-aligned).
- Desk busts (UI): **96 × 96** rendered from the same rig with a minimal code-drawn face (eyes/mouth overlays), 3 expressions
  (neutral, distressed, relieved); dialogue portraits 64 × 64.

### 7.4 Pipeline (adopt 03 §7 with these settings)
`tools/blender/*.py` (bpy geometry from `read_factory_settings(use_empty=True)`) → Cycles CPU, threads 4, **64 spp**, adaptive off,
denoise off, pixel filter **GAUSSIAN width 0.01**, `film_transparent`, view transform **Standard**, look None, max bounces 2, lights as 03 §7.2,
fixed seed → `tools/procgen/post.py` (alpha threshold 128; **ambient tint `#9e94cc` multiplied into non-emissive pixels**; nearest Border-24
colour, luma-weighted; outline; sheet pack; manifest) → `game/assets/**.png + .json`, committed. Entry point: `python3 tools/build_assets.py`
(whole prototype < 30 s). Build **fails** on any off-palette pixel or unexpected edge contact. Seed code: `tools/experiments/art/{lib,post}.py`.
Pin bpy 5.3; CI regenerates and diffs. Palette single source: `tools/procgen/palette.py`.

## 8. Technical standards (owner: Technical; adopt 04 unless changed here)

### 8.1 Rendering & display (04 §1–§2)
Pure 2D, pre-rendered sprites, `TileMapLayer` (isometric, diamond-down) + Y-sort. Compatibility renderer everywhere. Landscape
(`sensor_landscape`). Base **640×360**, stretch `canvas_items`, aspect `expand`, `scale_mode=integer`; default texture filter Nearest,
`snap_2d_transforms_to_pixel=true`, lossless sprite import. Safe area via `DisplayServer.get_display_safe_area()`.
**Lighting (C10):** no `CanvasModulate` and no `PointLight2D` in the prototype — the cold ambient is baked by post.py (§7.4); warm pools
are additive glow sprites (03 `fx/light_pool_*`) sharing **one** `CanvasItemMaterial` (blend ADD); flicker by swapping 2–4 frames.

### 8.2 Grid math (64×32; constants in `core/iso.gd`, class `Iso`; no inline maths anywhere)
- `TILE = Vector2(64, 32)`, `HU = 16`, `STOREY = 96`.
- Cell centre → local: `x = (cx − cy)·32 + 32`, `y = (cx + cy)·16 + 16` (= `TileMapLayer.map_to_local`).
- Local → continuous cell (after subtracting (32,16)): `gx = x/64 + y/32`, `gy = y/32 − x/64`.
- Levels: level L layers at `position.y = −L·96`, `y_sort_origin = L·96`, `z_index = L·10` (04 §3, rescaled). Cell height 0..5 HU applied as
  sprite offset `−h·16`. Anything taller than one storey **that has a level above it** is sliced into 96-px segments; free-standing tall props
  in single-level areas are not sliced.
- Multi-cell props: 1×1 footprints, except the prototype statue (2×2, solid, sort origin = its front cell, 1-cell walkable margin).
- Walkability: `AStarGrid2D` per (area, level), `DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES`; legal step if |Δh| ≤ 2 HU and Δh ≠ 0 only on stair cells.
- Movement: `gpos` continuous; player speed **3.0 cells/s** (config); interaction radius 1.5 cells; facing = nearest of 8 by screen-space velocity.

### 8.3 Project layout
As 04 §4 exactly (`game/` = `res://`; `game/data/` all content JSON; `game/assets/` generated only, plus vendored fonts in `assets/fonts/`
with licence files; `tools/` never shipped). Naming as 04 §4. Content ID prefixes `case_ npc_ dlg_ area_ rank_ flag_ item_ obj_`;
case-internal IDs: entries `r1`, hidden `h1`, archive `arc_002a`, discoveries `d_<word>`, questions `q1`. Narrative refs map
`S-004 → case_s004`, `ARC-004a → arc_004a`.

### 8.4 Autoloads (04 §4.1, in order)
`EventBus`, `Content`, `GameState`, `Clock`, `Sim`, `World`, `Dialogue`, `SaveGame`, `Audio`, `Playtest`.
Changes: **`Clock`** holds day/minutes and exposes `advance(minutes, reason)`; it has no real-time tick. **`Sim`** has two inputs:
`Sim.advance_game(minutes)` (counters, §6) and a 4 Hz real-time presentation tick (agent walking, queue shuffles). Scoring is a pure
static class `judgement/scoring.gd`, no autoload.

### 8.5 Data formats (04 §5 base; additions below are STANDARD)
Conditions/effects mini-language as 04 §5.1, plus ops — conditions: `stat_lte`, `discovered{case,id}`, `asked{case,id}`,
`case_state{case,value}`, `day_eq`; effects: `advance_clock{minutes}`, `give_archive{case,id}`, `call_soul{case}`, `reopen_case{case}`,
`snapshot_stats{tag}`, `restore_stats{tag}`, `reset_cases{ids}`, `start_incident{id}`, `buy_item{id,price}`.

**Case** `data/cases/case_s004.json` — fields:
`id, ref, name, age, era, place, cause, summary, portrait{seed,tags}, type, min_rank,`
`entries[{id, tag, weight, text≤80, ink:"black"|"violet"}], hidden[{id, tag, weight, text≤80}],`
`archive[{id, title, cards[≤3 × ≤80], requires[conditions]}],`
`discoveries[{id, triggers[{link:[entry,arc]} | {archive:arc} | {question:q}], ops[{op:"void"|"reweight"|"reveal", entry, weight?}], fact{text≤80, side?}, key:bool}],`
`questions[{id, text, kind:"general"|"confront", requires[conditions], answer[≤3 boxes ≤140], card≤80, fact?{id,text,side,key}}],`
`expected{tally_filed, tally_corrected, guideline}, epilogue{heaven, hell}, verdicts{heaven{effects}, hell{effects}}, ext{}`.
Weights are data; G is computed, and `validate_content.py` fails if computed tallies ≠ `expected`.

**NPC / dialogue / area / ranks / save**: as 04 §5.3–§5.6 with these values: stats in `ranks.json` = `merit` 0, `order` 68 (0–100),
`purse` 12 ("Obols"), `queue` 24 (derived), `overturned` 0, `cases_processed` 0, hidden `favour_gilt`, `favour_ember`, `conscience`.
Save `cases.<id>` additionally stores `composure, asked[], links[], discoveries[], ground, merit, sound`; one autosave slot.

### 8.6 Signals (EventBus; 04 §4.1 list plus)
`case_called(case_id)`, `discovery_made(case_id, discovery_id)` (replaces `evidence_revealed`), `link_attempted(case_id, entry_id, arc_id, ok)`,
`composure_changed(case_id, value)`, `case_scored(case_id, result: Dictionary)`, `shift_started(day)`, `shift_ended(day, summary: Dictionary)`,
`incident_changed(incident_id, state)`, `clock_ticked(day, minutes)` (now fires per `advance`).

### 8.7 Performance & export
Budgets as 04 §7 (60 fps target / 30 floor, ≤ 100 world draw calls, ≤ 600 sprites, atlases ≤ 2048², ≤ 64 MB textures, ≤ 4 ms GDScript).
Android preset arm64-v8a, min SDK 24, immersive; iOS later. No device here — see REVIEW risk R4.

### 8.8 Testing (04 §8 adopted)
`tools/run_tests.sh` = content validation → headless unit tests → rendered scripted playthroughs → screenshot gallery. Required unit tests
in addition to 04 §8.2: every row of §3.3 table; every prototype case reachable to all key facts with 0 wrong links within 3 Composure;
each ambiguous case has ≥ 2 facts per side; promotion gate pass/fail/correction branches; Order and pay formulas against §6 examples.

## 9. UI/UX standards (owner: UI/UX; adopt 05 unless changed here)

### 9.1 Controls (05 §3)
Tap-to-move (primary) + floating joystick on drag (secondary; 8 directions snapped to iso axes). Tap = release < 200 ms and < 12 px.
Joystick base 96, knob 40, dead zone 10. Tapping an interactable walks there and interacts. Context button bottom-right 64×64 (Talk, Enter,
Sit, Read, Take). Touches starting on HUD never move the player. **Touch targets ≥ 48×48 base px**, primary 56–64, ≥ 8 px apart.
Keyboard WASD/arrows + E/Esc for desktop testing.

### 9.2 HUD (05 §4 with D2)
```
+-------------------------------------------------------------------------------+
| [crest] Clerk's Court                 (!) Take a soul to your desk   +-------+ |
|         Day 1 - 09:30                     Merit 9/30                 |minimap| |
| [soul] 24  [obol] 12  [star] 68%                                     | 72x72 | |
|                                                                      +-------+ |
|                       isometric world, full-bleed                              |
| [Map] [Journal] [Pause]                                                [ TALK ]|
+-------------------------------------------------------------------------------+
```
Top-left panel 168×56: crest, location, day/time, **Queue / Obols / Order** (tap = 2-s tooltip). Top-right: one-line objective strip
(tap to expand) + 72×72 minimap (prototype: static 5-room schematic, current room lit, objective blip). Bottom-left bar **Map / Journal / Pause**
only (48×48). Map (prototype) = room graph; Journal = objectives, case notes, last 20 dialogue lines, pocket-ledger pages later; Pause =
Resume / Settings / Save & quit. HUD hides in dialogue, desk and ceremonies. Notifications slide from the top-left panel, never modal.

### 9.3 Desk screen (prototype; 05 §6.2 layout, these changes)
Columns at 640: booth 132 | tabs 48 | document 316 (grows on wide phones) | actions 96; margins 12, gaps 8.
- Booth: 96×96 bust, name, 3 **Composure pips**, expression change, last line.
- Tabs: **FILE** (summary), **RECORD** (entries as cards with weight pips: halo pips = virtue, flame pips = sin, dash = neutral; voided struck
  through; reweights show old→new; revealed hidden entries marked new; violet entries in `#8b3fd9` with the RM 0 margin stamp after discovery;
  bottom line "Rubric: +1 → Gilt Gate" updates live from the *known* record), **ARCHIVE** (received documents' cards), **TALK** (questions,
  answers as cards), **NOTES** (facts = grounds).
- Actions: **LINK** (enabled when one RECORD card and one ARCHIVE card are selected; selection persists across tabs; correct → red thread
  "Discrepancy" and the discovery; wrong → "No discrepancy", −1 Composure) and **PASS JUDGEMENT** (always enabled). No free-flag/auto-detect.
- Answers play in a dialogue-style panel over the desk (≤ 3 boxes), then persist as an 80-char TALK card.
- Leave desk any time; the case and the seated soul persist.
- Verdict view: 05 §6.3 plus a **Grounds** slot on the writ (pick one NOTES fact or "No ground"). Tap Heaven (left, halo) or Hell (right,
  flame) → hold 0.6 s on the writ (tap-to-confirm setting ships in the prototype) → thunk, shake 2 px, haptic 40 ms → soul leaves by its
  door → epilogue line (02 "If Heaven/If Hell") → **audit slip** (parchment, ≤ 5 rows: Diligence x/3, Verdict Upheld/Overturned/Noted,
  Ground Sound/Unsound/None, Merit +n, Order ±n) → tap → player stands.
- Archive at rank 1 = walk to Pell. The pneumatic tube (05 §6.2) is a rank-2+ convenience.

### 9.4 Other screens
Dialogue panel as 05 §5. Shift ledger as 05 §7 with rows: Souls processed (halo n / flame n); Discoveries x of y; Overturned n;
Pay +n → purse; Order %; Merit n/30 — plus one note (Marrow). "Sign and leave" autosaves. Promotion ceremony as 05 §8 with privileges:
[key] "The stair in Clerk's Court is open to you", [quill] "Appeals may now be heard", [obol] "Base pay 8 → 12 obols".
Settings (prototype): text speed, hold/tap stamp, joystick on/off, haptics, screen shake. Onboarding: in-world, by Marrow (05 §10, adapted in §10.5).

### 9.5 Style tokens (UI chrome; world sprites use §7.1 only)
Charcoal panel `#1a1722` @ 92 %; panel edge `#37323f`; border gold `#e0a83e`; Heaven gold `#f6d67a`; Hell red `#b3261e` / ember `#e8552b`;
selection/focus `#9a86ad` on charcoal, `#6a5484` on parchment; UI-only extras: parchment `#E6D9B8` / shade `#CBB98F`, ink `#2A2320`,
text light `#EDE6D6`, text dim `#A59E90`; Room-0 violet `#8b3fd9` (reserved). Gold may be neutral chrome and world light, but inside
judgement screens gold/red mean **only** Heaven/Hell; no warning is ever red. Contrast ≥ 7:1 for body text.

### 9.6 Fonts (C17) — all licences permit bundling; vendored with licence files, fetched once by a tools script
| Role | Font | Licence | Size |
|---|---|---|---|
| Display (≤ 3 words) | Jacquard 24 | SIL OFL 1.1 (google/fonts, reachable) | 24 / 48 |
| Body | Pixel Operator (+Bold) | CC0 | 16 |
| Numbers/ledgers | Departure Mono | SIL OFL 1.1 (reachable) | 11 / 22 |
| Large-text body | Jersey 20 | SIL OFL 1.1 (reachable) | 20 |
Any font that cannot be vendored for an offline build → that role uses **Godot's default font**, 16 px, antialiasing off (layouts are sized for it).
Pixel Operator's canonical source was not reachable from this environment; verify before M1 or fall back.

### 9.7 Text budgets (writers must hit these; validator enforces)
Dialogue box ≤ 140 chars / 3 lines; ≤ 4 choices; answer ≤ 3 boxes; record/archive/fact/answer card ≤ 80 chars (2 lines); ≤ 5 cards per page,
≤ 3 pages per tab; ≤ 4 visible questions; archive doc ≤ 3 cards; epilogue ≤ 2 boxes; objective strip ≤ 40 chars; audit slip ≤ 5 rows;
ledger ≤ 6 rows + 1 note; blackletter ≤ 3 words. Essential text ≥ 16 px; captions ≥ 12 px and never carry meaning alone.

---

## 10. PROTOTYPE SPEC (M1) — build exactly this

### 10.1 Scope
Rank 1 only; 5 areas; 2 shifts (Day 1, Day 2); 6 cases; promotion to Senior Adjudicator; 15–20 min for a first-time player.
Out: staff management, budget, upgrades beyond the lamp, remand, appeals, witnesses, envoys, Diplomatic Quarter, Border Guard HQ,
multi-level areas, CanvasModulate/lights, save slots (one autosave), music (ambience + SFX only), procedural cases.

### 10.2 Areas (ASCII = grid space: column = cx, row = cy; (0,0) is the top corner on screen; row 0 = far NE wall, column 0 = far NW wall;
last row/column = near kerbs `k`). Legend: `#` wall, `k` kerb, `D` door, `.` floor, `s` stair (h 2/4 HU), `g` gold inlay decal (walkable),
`T` statue (solid), `B` brazier, `p` wall plaque/hatch, `q` queue slot (soul-only), `r` rail, `d` desk, `o` stool, `b` bench seat,
`c` counter, `S` tall shelf, `e` empty shelf, `x` roped off, `n` ivy bench, `t` ticket booth, `=` dais carpet; letters for NPCs (§10.3).

**Clerk's Court** `area_clerks_court` 14×14 (outdoor hub; Gilt backdrop left, Ember right)
```
####D#####D###   row 0: D(4,0) stair door to Chambers; D(10,0) Records
#B.sss.....B.k
#..sss.......k
#...G........k   G = Grist (4,3) at the stair foot
p............k   p = Works Office hatch (0,4), use cell (1,4)
#....gggg....k
#....gTTg....k   statue 2x2 (6..7, 6..7) on 4x4 inlay ring
#....gTTg....k
D....ggggW...k   D(0,8) Arrival Hall; W = Wren (9,8)
#............D   D(13,9) Judgement Booths
#............k
#B..........Bk
#............k
kkkkkkkkkkkkkk
```
**Arrival Hall** `area_arrival_hall` 12×10 (gold windows NW wall, red NE)
```
############
#.......t..k
#qqqqqqqq..k     4 lanes x 8 slots = 32 (06 §11); head of each lane at cx 8
#rrrrrrr...k
#qqqqqqqqdRk     R = Registrar (10,4) behind desk (9,4); use cell (9,5)
#rrrrrrr...D     D(11,5) Clerk's Court
#qqqqqqqq..k
#rrrrrrr...k
#qqqqqqqq.nk     Nan Whitlow at slot (1,8); Percival Oddy at slot (8,2)
kkkkkkkkkkkk
```
**Records Annexe** `area_records_annexe` 10×8
```
##########
#SSSSSeSSk       empty shelf (6,1) (story hook)
#S.......k
#S...P...k       P = Pell (5,3); counter row 4; use cell (5,5)
#S.cccc..k
#S.....xxk       collapsed aisle roped off
#......xxk
kkDkkkkkkk       D(2,7) Clerk's Court
```
**Judgement Booths** `area_booths` 14×8 (player workplace; Gilt door left, Ember door right)
```
###p######D###   p = Rubric plaque (3,0); D(10,0) Ember Gate passage (red, souls only)
#....=M=.....k   M = Marrow (6,1) on 1-HU dais
D....=d=.....k   D(0,2) Gilt Gate passage (gold, souls only); Marrow's desk (6,2), use cell (6,3)
#..1...2..P..k   1,2 = NPC adjudicators (3,3),(7,3); P = player's seat (10,3)
#..d...d..d..k   desks; player desk (10,4)
D..o...o..o..k   D(0,5) Clerk's Court; stools; docket soul sits at (10,5)
#bbbbbbbbbbbbk   bench J: 12 seats
kkkkkkkkkkkkkk
```
**Adjudicator's Chamber** `area_adjudicator_chamber` 8×8 (end of prototype): far walls with one gold (NW) and one red (NE) window;
large desk at (4,3); `D(3,7)` back to the court. Entering it via the stair plays the rank title card.

**Connections** (0.25 s fade; arrival spawn cell in brackets):
court D(0,8) ↔ arrival D(11,5) [arrival (10,5) / court (1,8)]; court D(10,0) ↔ records D(2,7) [records (2,6) / court (10,1)];
court D(13,9) ↔ booths D(0,5) [booths (1,5) / court (12,9)]; court stair (3..5, 1..2) → chamber D(3,7) [chamber (3,6) / court (4,4)].
The stair is a **scripted climb** (player steps over the 3 stair cells with height offsets 0→2→4 HU, then fades); stair cells are solid until
`rank ≥ 2`. Measured legs at 3.0 cells/s: desk → Registrar ≈ 22 cells ≈ 8 s; desk → Pell ≈ 19 cells ≈ 7 s.

### 10.3 NPCs
| ID | Name (02) | Area / cell | Role in prototype | Lines |
|---|---|---|---|---|
| `npc_marrow` | Ignatia Marrow, Senior Adjudicator | booths (6,1) | Dockets, tutorial, shift ledger, promotion | 02 §7 1–7 + new (§10.7) |
| `npc_pell` | Osric Pell, Under-Archivist | records (5,3) | Hands over the active case's archive docs | 02 §7 1–6 |
| `npc_wren` | Tobias Wren, Junior Processing Clerk | court (9,8) | Gossip after cases | 02 §7 1–6 (re-tagged §10.7) |
| `npc_grist` | Sgt. Hob Grist | court (4,3) | Blocks stair; resolves incident; salutes after promotion | 02 §7 1–6 |
| `npc_registrar` | the Registrar (name TBD by Narrative) | arrival (10,4) | "Call next": hands over the docket soul + file | new, 3 lines |
| `npc_clerk_a/_b` | anonymous adjudicators | booths (3,3), (7,3) | Take bench souls (1.2/game-h total) | none |
| `npc_works_hatch` | Works Office clerk (hand in a hatch) | court hatch (0,4) | Sells the desk lamp (20 ob) | new, 2 lines |
| `npc_nan`, `npc_oddy` | Nan Whitlow, Percival Oddy | arrival (1,8), (8,2) | Ambient souls, talkable | 02 §7 |
| docket souls | the 6 case souls | spawned at the Registrar | Follow the player 1 cell behind; sit on stool (10,5) | case data |
| crowd | queue souls ≤ 32, bench ≤ 12, 4 wandering clerks in the court | zones | Crowd sprites; no logic | — |

### 10.4 Cases (docket order fixed)
| Shift | Case | Type / G | Key facts (trigger) | Teaches |
|---|---|---|---|---|
| Day 1 | case_s001 Marta Ellingsen | clear / Heaven | `k_coal` (q2 answer, side Heaven) | Walk, call, read, stamp, door, slip |
| Day 1 | case_s002 Aldous Pryke | contested / Hell | `d_almshouse` (link r1↔arc_002a, reweight r1→0); `d_two_ledgers` (archive arc_002b → h1) | Records trip; LINK |
| Day 1 | case_s003 Ned Garrity | contested / Heaven | `d_gas_rescue` (archive arc_003 → h1); `k_front_door` (q3 confront answer, Heaven) | Archive reverses the file; interview |
| Day 2 | case_s004 Wim Daelmans | contested / Heaven | `d_in_custody` (link r2↔arc_004a, void r2); `d_enemy_boy` (arc_004b or q2 → h1) | Two routes to one fact |
| Day 2 | case_s007 "Tomas Verhoek" | ambiguous / (+1) | `d_false_name` (link r4↔arc_007a → h2; unlocks confront q2); `d_kell` (q3, confront after q2 → h1, h3; q3 also gives fact `f_confessed`, side Heaven, not key); `d_widows` (arc_007b, requires `d_kell` → second Pell visit → h4) | Addendum trip; grounds on either side |
| Day 2 | case_s008 Bess Tarrow | contested / Heaven (plot) | `d_violet_ink` (link r2↔arc_008a, void r2; sets `flag_found_violet_ink`); `d_ribbon` (link r1↔arc_008b, reweight r1→0); `d_mill_race` (arc_008c or q3 → h1) | Room 0; promotion |
Question kinds: S-001 q1–q3 general; S-002 q1 general, q2 confront (after d_almshouse), q3 confront (after d_two_ledgers); S-003 q1–q2 general,
q3 confront (after d_gas_rescue); S-004 q1–q3 general; S-007 q1 general, q2 confront (after d_false_name), q3 confront (after q2);
S-008 q1–q3 general. S-005 and S-006 are not in the prototype (pacing and case mix; kept for M2).

### 10.5 Player flow (boot → promotion)
1. Boot → title (New / Continue / Settings). New → card "Day 1 — 08:00, the Arrival Hall". Player spawns at arrival (10,6). Clock frozen until step 3.
2. Registrar: "Staff go through the Court to the Booths." Objective "Report to Ignatia Marrow". Passing the court: Wren line 1, Grist line 1 if approached.
3. Booths: talk to Marrow → line 1, docket S-001..S-003 → `shift_started(1)`, clock 08:00. Line 2. Objective "Call your first soul".
4. Arrival: Registrar → "Call next" → `call_soul`, A −1; Marta follows. Booths: tap desk → sit; soul takes stool → desk screen.
5. S-001: read, (q2), PASS JUDGEMENT → stamp → exit door → epilogue → audit slip. Player stands.
6. Marrow line 3 → objective "Fetch Pryke's originals from Pell". Call S-002; Records: Pell line 1/2 → arc_002a, arc_002b (+15 min; h1 auto-revealed).
   Desk: link r1↔arc_002a → stamp. Marrow line 4.
7. Marrow line 5 → S-003 (Records → arc_003 → h1; q3 unlocks). After the S-002 verdict the **incident** starts: a wandering soul
   at court (5,4) tries the stair; talking to Grist before the S-003 verdict = Resolved (+4 Order), else Unresolved (−4; Grist escorts it anyway).
8. After S-003: Wren line 3 (court). Report to Marrow → **shift ledger** (pay, Order, Merit) → Sign → autosave → `snapshot_stats("shift1")`.
9. Day 2 card, 08:00, spawn at booths (1,5). Optional: Works hatch → buy lamp (20 ob). Marrow: docket S-004, S-007, S-008 (no more tutoring).
10. S-004 (Records optional; q2 alternative). Wren line 4. S-007 (Records → link r4 → q2 → q3 → second Pell visit for arc_007b). Wren line 5.
11. S-008 → Pell line 5 when handing arc_008a; desk: violet entry visible; link r2↔arc_008a → RM 0 stamp appears. Stamp verdict.
12. Gate (§4): pass → promotion scene 02 §8 at Marrow's desk with the three-way choice (`flag_tarrow_file` = forwarded / kept_copy / misfiled)
    → ceremony card → cuffs change. Violet ink missed → Pell correction → re-stamp → re-check. Merit/Overturned fail → "Docket reissued".
13. Court: Grist line 6, stair unlocks → scripted climb → Adjudicator's Chamber → title card **SENIOR ADJUDICATOR** — *"The file is a claim.
    You are now the second opinion."* → "End of prototype" summary (Merit, Order, obols, choices) → title.

### 10.6 Stats & thresholds (all in `data/config.json`)
Composure 3; clock costs §2; Queue start 24 (A 16, J 8); Order start 68; purse start 12; lamp 20; Merit gate 30/54; Overturned ≤ 2;
`flag_found_violet_ink` required; speed 3.0 cells/s; interaction radius 1.5 cells.

### 10.7 Content tasks (Narrative, before M1 content freeze)
Registrar name + 3 lines; Works hatch 2 lines; archive facsimile cards (≤ 3 × 80 chars) for arc_002a/b, 003, 004a/b, 007a/b, 008a/b/c and
the S-001 "nothing contradicts" note; 80-char cards for every answer and fact; Marrow: "Six souls" (not eight) in 02 §8, shift-1 and
shift-2 closing notes, "Docket reissued" line; Pell correction scene (3 boxes); incident soul line; Wren re-tags: line 4 after S-004,
line 5 after S-007. Split any line over 140 chars.

### 10.8 Reference playthroughs (scripted in `tests/playthroughs/`)
| Profile | Per case (S-001, 002, 003, 004, 007, 008) | Merit | Overturned | Outcome |
|---|---|---|---|---|
| perfect | 9 each | 54 | 0 | promoted |
| attentive | 4, 9, 7, 7, 7, 9 | 43 | 0 | promoted |
| half-diligent | 4, 9, 9, 0, 0, 9 | 31 | 1 | promoted |
| rubric-only (never visits Records, asks all) | 9, 0, 0, 0, 0, 0 | 9 | 4 | correction, then reissue |
| careless (stamps at once) | 4, 0, 0, 0, 0, 0 | 4 | 4 | correction, then reissue |

### 10.9 Required assets (generated; sizes in px)
| Group | Assets |
|---|---|
| Tiles | `floor_flag` 64×32 ×4; `floor_flag_edge` 64×48 ×2; `floor_carpet_red` ×3; `floor_goldseam` ×2; `decal_inlay_ring` 256×128 |
| Walls | `wall_plain_{x,y}`, `wall_window_{x,y}` (gold + red glass), `wall_door_{x,y}` (open/closed), `wall_door_gilt`, `wall_door_ember`, `wall_corner` 64×128; `wall_kerb_{x,y}` 64×48; `stairs_{x,y}` 64×80 |
| Props | brazier 32×48 ×4; wall_torch ×4; banner_red 32×96 ×2; desk_clerk 64×64 ×3 (in-tray); desk_superior 64×80; dais; stool; bench 64×48 (+ seated-soul variant); lectern; plaque; works_hatch; shelf_books / shelf_tall (incl. empty); counter; rope post; queue_rail_{x,y}, queue_post; ticket_booth 64×112; statue_first_clerk 128×192 |
| Characters (8 dirs) | player idle 8×2, walk 8×4 (+ `player_r2` cuff variant); clerk idle/walk/work (hem tints grey, lilac) for Marrow, Wren, Registrar, NPC clerks; archivist (Pell) idle/walk; guard 32×64 idle/walk/attention; soul idle/float × 4 body variants |
| FX | shadow_blob 32×16; select_ring ×4; light_pool_gold/red 192×96 ×2; dust_mote 8×8 ×4; tap marker 16×8 ×4 |
| Backdrops | heaven_sky 640×360, heaven_skyline 960×240; hell_sky, hell_skyline (Bayer-dithered); void_fog 256×128 |
| UI | 05 §13 list, minus settings-bar icon (settings lives in Pause), plus composure pip 16×16, LINK icon, grounds slot, RM 0 stamp 64×32, lamp icon |
| Portraits | 64×64: Marrow, Pell, Wren, Grist, Registrar, works clerk, generic soul; busts 96×96 × 3 expressions: 6 case souls |
| Audio (synthesised by script) | tap, page flip, quill tick, door, stamp thunk, bell; one ambience loop per area |
| Fonts | §9.6 (vendored, licences beside them) |

### 10.10 Acceptance tests — the prototype is done when…
1. `tools/run_tests.sh` is green: content validation, all unit tests (incl. §3.3 rows and §8.8 list), all five §10.8 playthroughs reach their stated outcome.
2. `python3 tools/build_assets.py` regenerates every asset from a clean checkout in < 60 s and produces a byte-identical diff (palette lint passes).
3. A fresh boot reaches the title in < 5 s (desktop) and New Game reaches control of the player with no error in the log.
4. The player can walk all 5 areas by tap and by joystick; every door and interactable is reachable (pathfinding test).
5. All 6 cases complete with both verdicts; leaving the desk mid-case and returning restores the case exactly (save → load → equal).
6. Killing the app mid-case and continuing resumes in the same area with the same case state.
7. The HUD shows Queue 24 / Obols 12 / Order 68 % at start and updates per §6; the bar contains exactly Map / Journal / Pause.
8. Screenshot gallery at 1280×720, 1920×1080 and 2400×1080 shows no clipped text, all touch targets ≥ 48 base px, safe-area margins honoured.
9. Draw calls ≤ 100 in the busiest area (Arrival Hall full queue) under the playtest driver.
10. No screen performs an action except at its physical origin (desk, Pell, Registrar, hatch, Marrow) — QA checklist sign-off.
11. Three people who have not seen the game finish in 15–25 min, and each can explain one Merit point they lost (Director's M1 criterion).

## 11. Roadmap after the prototype (Director 01 §7, amended)
| Milestone | Content | Exit criterion |
|---|---|---|
| M1 First playable | §10 | §10.10 |
| M1.5 Device check | First Android build on a physical mid-range phone (outside this container) | ≥ 30 fps, touch thresholds tuned, text readable |
| M2 Rank 2 slice | Judgement Chambers (first multi-level area), appeals, remand, witnesses, 2 grounds, tampered ledgers, S-005/S-006 + 8 new cases, pneumatic tube, Journal pocket-ledger pages, desk Reports ledger, act 2 opening | 45–60 min; rank 1→2→gate of 3 |
| M3 Case pipeline | Authoring guide, validator, 40+ cases, templated filler cases | New case with no code change |
| M4 Rank 3 management | Admin Offices, roster board (Staff), Works Office (Upgrades), 06 tiers A–D, employees, events, Order formula from 06 §5 | Management done entirely on foot |
| M5 Rank 4 politics | Diplomatic Quarter, gates, envoys, favours, quotas, summit; HUD coin = treasury (mockup values) | Favour visibly changes the fortress |
| M6 Rank 5 + ship | Chancellor's Office, audiences, endings, balancing, store builds | 12–15 h campaign on mid-range Android |

## 12. Working agreements
| Area | Owner | Must consult |
|---|---|---|
| Loop, judgement, scoring, progression, gates | Director | Narrative, Management, QA |
| Lore, names, characters, case content, dialogue | Narrative | Director (case types), UI (budgets) |
| Look, palette, sprite conventions, art pipeline | Art | Technical (manifests, standards) |
| Engine standards, data formats, grid math, autoloads, tests | Technical | QA |
| Controls, screens, HUD, text budgets, fonts | UI/UX | Director, Narrative |
| Simulation & economy formulas | Management | Director |
| This document, REVIEW, playthroughs, definition of done, arbitration | QA/Producer | everyone |
- **Changes:** edit `PROJECT.md` in a branch/PR titled `[§N] <change>`; the section owner approves; any change to a STANDARD (§7.2, §8)
  also needs Technical + QA; QA checks cross-references and updates `REVIEW.md` if a contradiction is resolved.
- **Owner rulings** go only into `DECISIONS.md` (append-only, next `D#`, date, source) and override everything here; QA then updates this document.
- Proposals `01`–`06` are frozen; do not edit them to match this document.
- Numbers live in `game/data/config.json`; balancing changes data, not code. Every playtest result that changes a threshold is logged in the PR.
