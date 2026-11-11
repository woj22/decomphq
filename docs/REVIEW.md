# Cross-Review of Proposals 01–06 — QA/Producer (Agent 7)

2026-11-10. Inputs: BRIEF, DECISIONS (D1 landscape, D2 in-world Staff/Reports/Upgrades), proposals 01–06, reference images.
Authority used: DECISIONS > BRIEF > owning role, except where another role's validated evidence beats an unvalidated choice.
Every ruling below is already applied in `PROJECT.md` (section given in brackets).

## 1. Contradictions and dependencies

| ID | Topic | Roles | Conflict | Ruling | Rationale |
|---|---|---|---|---|---|
| C01 | Tile / scale | Tech, Art, UI | 04: 32×16 tile, 24×40 cell, figure ~12×24. 03: 64×32 tile, ~36 px figure in 32×56 cell (validated renders). | **64×32 tile, HU 16 px, storey 96 px, cell 32×56, figure ~36 px, 640×360 base** [§7.2, §8.2] | On a 6" 20:9 phone 1 base px ≈ 0.175 mm: a 32×16 tile is 5.6×2.8 mm (too small for a thumb tap), a 24-px figure 4 mm. At 64×32 a tile is 11×5.6 mm and a figure 6.3 mm. Art's size is rendered and seamless (art-test-room); Tech's geometry is the same camera at half scale, so only constants change. ~10 tiles across is enough for 12×10 rooms. |
| C02 | Blender `ortho_scale` | Tech, Art | 04: `render_width/22.627`. 03: `max(W,H)/45.2548`. | **`max(W,H)/45.2548`** [§7.2] | Blender's ortho scale spans the larger side. 04's width form is wrong for tall sprites (64×128 walls). |
| C03 | Grid axes | Tech, Art | 04/Godot: +x = SE, +y = SW. 03: +X = SE, +Y = NE. | Godot convention; Blender `(X,Y) = (cx, −cy)` [§7.2] | Engine math must match `TileMapLayer.map_to_local`. The pipeline adapts. |
| C04 | Facings | Tech, Art | 04: 4. 03: 8 (measured cost ≈ 0.016 s per frame). | **8 directions**, order stored in the manifest `dirs` [§7.2] | Joystick is 8-way and A* moves diagonally. Four facings would make screen-horizontal walks look wrong. The extra cost is negligible. |
| C05 | Verdict scoring | Dir, Narr, Mgmt, UI | 01: Merit 0–9 with types. 02: additive weights, judged on the corrected record. 06: sound/unsound drives Order and pay. 05: no right/wrong flash. | One model: G = Rubric on the **corrected** record. **Sound** = verdict == G (clear/contested), or any verdict (ambiguous). Merit = max(0, Diligence 0–3 + Verdict +4/−2, or +4 if ground matches on ambiguous cases, + Ground +2). Ground = one *discovered* fact; its side = sign of its tally change. The audit slip appears after the soul exits [§3] | Keeps 01's structure, 02's numbers and 06's inputs. Fact sides come from weights, so they never need hand-authoring. Checked against S-002, S-004, S-007 and S-008 in §3.3. Visible entries cannot be grounds, because then grounds would be free. |
| C06 | Diligence denominator | Dir, Narr | 01 assumes 3 key facts per case. 02's cases have 0–4 discoveries. | `key` facts 1–3 per case; Diligence = floor(3·found/total) [§3.1, §10.4] | Fits every 02 case without rewriting it. S-001 gets an interview key fact. |
| C07 | Clock | Dir, Mgmt, UI | 06: real-time 10-min shift that runs at the desk. 01: per-action clock, no fail timers. | **Action-driven clock** (door +5, question +10/+5, archive +15, verdict +20). The sim advances by game minutes [§2, §6] | Director owns the loop. P5 needs a reading-heavy game to be interruption-safe. The queue still grows with time spent, which keeps 06's diligence-vs-throughput tension. |
| C08 | HUD stats | Dir, Mgmt, UI, Narr, mockup | Processed/Coin/Order (01), Waiting/Purse/Order (06), "waiting, wages, standing" (05), Docket/obols/Order (02). Mockup shows 124 / 2,750 / 68 %. | **Queue 24 / Obols 12 / Order 68 %** in the prototype. The mockup values are 06's fortress-wide Day-1 numbers for a rank 4+ HUD [§6, §9.2] | Management owns the formulas and Narrative owns the names ("the queue", obols, Order). Merit goes on the objective strip. |
| C09 | Bottom bar | D2 vs 01, 06 | 01 P1/§6.7 keeps Map/Staff/Reports/Upgrades, with buttons present but disabled. 06 §8 puts a pocket ledger on the bar. | **Map / Journal / Pause only.** The pocket ledger becomes Journal pages. Settings sits inside Pause [§1, §9.2] | D2 is binding. |
| C10 | Lighting and emissives | Tech, Art | 04 uses CanvasModulate. 03 says emissives must not dim and that multiply turned windows lilac. | No CanvasModulate or PointLight2D in the prototype. post.py bakes the `#9e94cc` tint into non-emissive pixels. Warm pools are additive glow sprites with one shared material [§7.4, §8.1] | Same look as Art's validated composite, with no renderer work and no batching break. Per-area runtime tint can come later with Tech sign-off. |
| C11 | Prototype case set | Dir, Narr, Mgmt | 5 cases over 2 shifts (01), 8 cases (02), 6–10 in one 10-min shift (06). | **6 cases, 2 shifts:** S-001/002/003 on Day 1; S-004/007/008 on Day 2. S-005/S-006 move to M2 [§10.4] | Fits 15–20 min. Covers each mechanic once (link, archive reveal, gated question, addendum trip, ambiguous case, plot case). S-008 must stay because it carries the promotion story. |
| C12 | Promotion gate | Dir, Tech, Mgmt, UI, Narr | 28/45 + ≤1 overturned (01); merit ≥ 30 + flag (04); processed ≥ 6, accuracy ≥ 67 %, Order ≥ 60 (06); standing 80 % (05); S-008 corrected (02). | 6/6 processed, `flag_found_violet_ink`, **Merit ≥ 30/54**, Overturned ≤ 2. If the ink was missed, S-008 is reopened for correction. Other failures reissue the Day-2 docket [§4] | Reference play: perfect 54, attentive 43, half-diligent 31 pass; Rubric-only ≤ 16 and careless 4 fail. Narrative's "correction, not fail state" is kept. Order is not part of the gate because it would only repeat the Overturned check. |
| C13 | Order deltas, coin | Dir, Mgmt | 01: +2/−6, Order start 60, +10 coin per case with no sink. 06: +2/−5, start 68, pay formula plus a lamp. | 06 values [§6] | Management owns the economy. The lamp gives coin a sink (01 risk 5). |
| C14 | Flagging | Dir, UI | 05: flags are free, and a contradiction is auto-detected when two flagged cards conflict (brute-forceable). 01: pair-tap, and a wrong pair costs 1 Composure. | Explicit **LINK** of one record card + one archive card. A wrong link costs −1 Composure. No auto-detect [§3.1, §9.3] | Director owns judgement. It closes the brute-force path (01 risk 2). The validator proves every key fact is reachable within 3 Composure. |
| C15 | Archive access | Dir, UI | 05: pneumatic tube from the desk ("later ranks walk"). 01/02: walk to the archivist. | Rank 1 walks to Pell. The tube is a rank 2+ convenience [§9.3, §11] | P1. Convenience is earned. 05 had the order reversed. |
| C16 | Desk location | UI, Dir, Narr | 05 puts the desk in the Judgement Chambers, which 01/02 lock until rank 2. | Rank-1 desk is in the **Judgement Booths**. The Chambers are the promotion reward [§10.2] | Consistency with the gate and the story. |
| C17 | Fonts | UI, Tech | 05 font list, availability unverified. 04: "one pixel + one body TTF". | 05 list adopted. All are OFL or CC0. Fonts are vendored with their licences. Any font that cannot be bundled offline falls back to Godot's default font at 16 px [§9.6] | Checked from here: the google/fonts OFL files (Jacquard 24, Jersey 20, Pixelify Sans) and Departure Mono are reachable. Pixel Operator's source is not verified. |
| C18 | Colour meaning | Art, UI, Narr | 03: gold = interactable, red = warning. 05: gold/red mean Heaven/Hell only. 02: violet is reserved for Room 0, while 05 uses purple for selection. | Gold/red mean only Heaven/Hell inside judgement screens. Red never means warning. Selection uses muted `#9a86ad`/`#6a5484`. Room 0 gets a distinct saturated `#8b3fd9` [§7.1, §9.5] | The UI must never hint at the verdict, and the violet ink is a plot beat. |
| C19 | UI palette | UI, Art | 05 hex tokens are off Border-24 (`#1B1A20`, `#C9A24B`, …). | Border-24 equivalents are used wherever one exists. Parchment, ink and text colours are UI-only extras [§9.5] | Art owns the palette. Documents need a parchment colour that the world palette lacks. |
| C20 | Touch target, body size | Tech, UI | 40 px / ≥ 10 px (04) vs 48 px / 16 px (05). | **48 px, 16 px** [§9.1, §9.7] | UI owns controls and screens. 16 px is also the fallback font size. |
| C21 | Soul faces | Art, UI | 03: souls are faceless. 05: busts have 3 expressions. | Faceless in the world. Desk busts are 96×96 with a minimal code-drawn face [§7.3] | Both survive: the world rule is about 36-px readability. |
| C22 | Near walls | Art, Tech | 03: dollhouse cut or 24-px low walls. 04: 1 HU kerb. | Kerb of 1 HU = 16 px (`wall_kerb_*`) [§7.2] | Tech's rule at the new scale. |
| C23 | Storey slicing | Tech, Art | 04 slices everything over 48 px. 03's statue is 160 px on a 2×2 footprint. | Slice at 96 px, and only where a level exists above. The statue is a documented 2×2 exception [§8.2] | Prototype areas are single-level. |
| C24 | Stair / levels | Tech, Dir | 01's locked stair needs a level change, which 04 verified only on a synthetic scene. | Prototype uses a scripted 3-cell climb then a fade. The first real multi-level area is in M2 [§10.2] | Removes an unvalidated risk from M1. |
| C25 | Upgrades place | D2, Mgmt, Dir | 06: Master Mason's table in the courtyard. 01: commission on site. | Commissioning happens at the **Works Office** (D2). The Mason staffs it, and the site changes visibly [§6] | D2 is binding. |
| C26 | Names | Narr vs 01, 04, 05 | "Codex", "Supervisor", "Supervisor Morwen", "Archivist Wren", stat `coin`, ID `case_miller`. | 02 names everywhere (Rubric, Marrow, Pell; Wren is a clerk; `purse` "Obols"). IDs `case_s004`, `arc_004a` [§5, §8.3] | Narrative owns names, Tech owns ID format. |
| C27 | UI copy | UI vs gate | Ledger shows "Standing 62 %, next rank at 80 %". Ceremony shows "Records opened" and "wages 60". | Ledger shows Merit n/30. Privileges: stair, appeals, pay 8→12 [§9.4] | Matches C12 and C15. |
| C28 | Player speed | Tech, Dir | 04: 3.5 cells/s. 01: legs of 10–15 s. | 3.0 cells/s. Legs measure 7–8 s on the prototype map [§8.2, §10.2] | Short legs suit mobile. The value is in config, so it is tunable. |
| C29 | Narrative text fixes | Narr, UI | Promotion line says "Eight souls". Some answers exceed 140 chars. Wren's tags fire after cases that are not used. | "Six souls". Lines are split into ≤ 3 boxes. Wren lines re-tagged [§10.7] | Follows from C11 and the §9.7 budgets. |
| C30 | Rank display | Narr, Art | 02: cuffs grey → gold-and-red. 03: player has a gold hem and NPC hem shows rank. | The player keeps the gold hem for identification. Rank shows on 2-px cuffs plus the HUD crest. NPC rank shows by hem [§7.3] | Both kept, and both readable at 36 px. |
| C31 | S-006 tally | Narr | The corrected −1 needs Q2 to be asked; without it the tally is 0. | Scored on the authored −1. Ambiguous, so unaffected. Fix by M2 [§3.3] | Found by re-tallying all 8 cases. The other seven match exactly. |
| C32 | Asset list scope | Art | 03 §9 includes bridges, envoys and spires, which no prototype room uses. It lacks kerbs, stool, plaque, gilt/ember doors, busts. | Trimmed and extended list [§10.9] | Prototype rooms (C11/C16). |
| C33 | Scale of souls | Mgmt, Narr | ~120 souls/day vs "every dead human". | Narrative decides by M4 (one gate of many, or a counted soul stands for a batch). Formulas are unaffected | Not blocking. |
| D1d | Dependency | Narr → all | Registrar name, archive facsimile cards, 80-char cards, new Marrow/Pell lines. | Content tasks in §10.7, due before M1 content freeze | Blocks the playthrough tests. |
| D2d | Dependency | Art → Tech | Manifest must carry `origin`, `dirs`, `fps`, `cell`. Ported pipeline code from `tools/experiments/art/`. | §7.4, §8.3 | Blocks task 15 in 04 §9. |

## 2. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | Procedural "chess-piece" characters lack charm (03 risk 1) | Silhouette props, hem colours, code-drawn pixel touch-ups. Busts carry the emotion. Review at the first screenshot gallery |
| R2 | Cycles renders read as "pre-rendered 3D" | Point-sampled filter, palette lock, brick rule, outline pass. Art spike on one kit before bulk generation (04 risk 5) |
| R3 | The fetch route (desk ↔ Pell ↔ Registrar) feels rote | 7–8 s legs, Wren and Grist lines on the way, S-001 skips Records, S-007 adds the addendum trip. Batch two souls per trip if playtests complain |
| R4 | No device, SDK or export templates here; performance and touch are unverified | M1.5 device check outside the container. Track draw calls and sprite counts in CI. Test touch with emulation at three window sizes |
| R5 | Scoring balance is arithmetic, not measured | Thresholds live in config. The five reference playthroughs are tests. Retune after the §10.10 test 11 sessions |
| R6 | Baked tint vs a future runtime tint (C10) | post.py keeps the `_e` masks as intermediates, so CanvasModulate plus an emissive overlay can be added later without re-rendering |
| R7 | The 2×2 statue and stair climb hit Y-sort edge cases | 1-cell walkable margin around the statue. The stair is scripted. Screenshot assertions cover both |
| R8 | Showing the live Rubric tally turns judging into arithmetic (02 risk 2) | The tally only uses the *known* record, so arithmetic still needs discovery. Ambiguous cases ignore the tally. Revisit in M2 (pips only, total hidden) |
| R9 | Heavy themes: execution (S-004), mercy killing (S-005), a child's death (S-006) | Non-graphic writing, no "correct" answer on S-005/S-006, a content note at first launch. Recommend PEGI 12 / ESRB T / IARC 12+ (Q2) |
| R10 | Content volume: 12–15 h needs about 150 cases | M3 pipeline, validator and templated filler cases. Hand-written landmark cases only |
| R11 | Font source drift or unavailability | Vendor the fonts once with licences and commit them. Fall back to Godot's default font (C17) |
| R12 | Determinism of art across Blender versions | Pin bpy 5.3. Fixed seeds. CI regenerate-and-diff |
| R13 | Scope creep into management or politics before M1 | §10.1 out-list. QA rejects M1 PRs outside §10 |

## 3. Owner input needed (≤ 5)

1. **Q1 Gameplay camera vs the mockup.** At playable scale (64×32 tiles, ~10 tiles across) the game shows one room at a time, while the
   mockup's whole-fortress vista becomes the Map and backdrop render. **Recommend: approve** (alternative: 32×16 tiles and tiny figures, which C01 found too small to tap).
2. **Q2 Age-rating target.** **Recommend PEGI 12 / ESRB Teen / IARC 12+**, keeping S-004–S-006 as written with a first-launch content
   note (alternative: 16+, or softening S-005/S-006).
3. **Q3 Religious terms.** In-fiction text uses the Principal and the Counterparty only. Should the single oath "God's teeth" (S-006) stay, and
   may store copy say "God and the Devil" as the brief does? **Recommend: zero exceptions in-game (Narrative replaces the oath);
   store copy says "Heaven and Hell" only.**
4. **Q4 Business model.** Premium or free-to-play? This decides whether obols ever touch real money and how the economy is tuned.
   **Recommend premium** (one purchase, no in-app currency), which matches the narrative focus and the "no timers" pillar.
5. **Q5 Device testing.** The container cannot build or run an APK. **Recommend:** the owner provides one mid-range Android phone (2019–21
   class) plus someone to sideload builds for M1.5, and a Mac for iOS later.
