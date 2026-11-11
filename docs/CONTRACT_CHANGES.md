# Contract changes

Append-only log of deviations from `CONTRACTS.md` (who, what, why).

## 2026-11-11 — Content (game/data, tools/validate_content.py, tools/schemas, tools/scoring_ref.py)

All additions are optional keys; nothing in CONTRACTS.md is removed or renamed. Engine readers should treat them as described.

1. **Discoveries may carry `effects`** (list of §3.2 effect ops), run once when the discovery is made, after its `ops`.
   Used by `case_s008` `d_violet_ink` → `set_flag flag_found_violet_ink true` (the promotion gate flag).
2. **Fact `side` is always authored** on discovery facts (§8.5 marks it optional). The validator fails if it disagrees with the
   sign of the ops' tally change, so Engine may read it directly instead of recomputing.
3. **`epilogue.heaven` / `epilogue.hell` are arrays of 1–2 boxes** (≤140 chars each), like `answer`.
4. **Verdict effects carry the hidden stats.** `verdicts.<side>.effects` add `favour_gilt`/`favour_ember` (+1 to the receiving side) and
   `conscience` (+1 Heaven-against-G or ambiguous Heaven, −1 the reverse). Engine must NOT also compute these in scoring.gd
   (Merit/Order/Overturned/cases_processed stay Engine-computed).
5. **Area objects may carry `conditions`** (§3.1 list; object hidden/inactive while false): the incident soul
   (`flag_incident_active`), the stair and the chamber door (`rank_gte 2`). A locked stair shows `locked_dialogue`.
6. **Stair object fields**: `cells` (the 6 `s` cells), `climb` (3 cells walked in the scripted climb), `climb_h_hu` ([0,2,4]), `to`.
   Legend `s` carries `solid_until` (a condition). The chamber door (4,0) has `"via":"obj_stair"`: it is reached only by the climb.
7. **Area `overrides`**: `[{cell, kind, prop, solid, h_hu}]` replaces the legend for one cell (Marrow's desk (6,2) is `desk_superior`
   while the other booth `d` cells are `desk_clerk`).
8. **Legend extras**: `h_hu` (dais height; non-zero cells are not walkable since only stairs allow Δh), `floor` (floor family for that
   cell), `sprite` (wall sprite for `p` cells: `works_hatch_y`, `wall_plaque_x`), `walkable` on `q` (queue cells ARE walkable by the
   player — Nan at (1,8) is only reachable through her lane), `footprint` on multi-cell props (`T` statue 2×2: draw once at the block's
   min cell). Decor entries may carry `footprint` too (`decal_inlay_ring` at its min cell (5,5), footprint [4,4]).
   Stools `o` are `seat` with `solid:false` and NPC letter cells are floor (actors do not block A*): otherwise the booths grid has no
   path from the door to the player's desk (column 7 is dais/NPC/desk/stool/bench).
9. **Object extras**: `facing` on npc objects; `desk_player` has `seat` and `soul_seat`; NPC clerks have `desk` + `soul_seat`;
   `soul_door` has `verdict`; `inspect` may name an `npc` instead of a `dialogue` (Marrow's desk = talk to Marrow).
   Arrival Hall spawn `soul_call` [8,5] is where `call_soul` materialises the docket soul.
10. **config.json extras**: `incidents.inc_stair_soul` (npc/area/cell/object/resolver), `ledger_notes.{day}` = list of
    `{conditions, text}` (first passing = Marrow's ledger note), `items.item_desk_lamp`, `start`, `promotion` (gate numbers; the
    validator checks `trg_gate_pass` uses the same values).
11. **ranks.json**: each rank has `auto:false` (Engine must not auto-promote on `requires`; the rank is set by `set_rank` in
    `trg_shift2_ended_promote` after the promotion scene and shift-2 ledger), plus `base_pay`, `sprite`, `crest`, `privileges`, `motto`.
12. **Trigger `match` argument names**: `area_entered{area_id}`, `case_called{case_id}`, `case_scored{case_id}`,
    `discovery_made{case_id, discovery_id}`, `dialogue_ended{dlg_id}`, `shift_started{day}`, `shift_ended{day}`, `rank_changed{rank}`.
    Several triggers may match one event; they are written to be mutually exclusive, so evaluation order does not matter.
    `once:false` triggers re-fire (the S-008 gate re-runs after a correction or reissue).
13. `set_flag.value` may be a string (`flag_tarrow_file` = `forwarded | kept_copy | misfiled`). `give_docket.day` / `start_shift.day`
    are ints; `config.dockets` keys are the same numbers as strings.
14. **Reference scoring oracle** `tools/scoring_ref.py` (stdlib; owned by Content per the M1 brief): reproduces every §3.3 row and the
    §10.8 playthroughs from the real case data. `judgement/scoring.gd` must match it. `tools/schemas/ops.json` lists every allowed op
    with argument types; Engine may load it.
15. Gate order when S-008 is scored: violet ink missing → Pell correction (repeats on every re-stamp until the ink is linked);
    ink found and Merit/Overturned/processed fail → "Docket reissued" (`restore_stats shift1` restores ALL stats incl.
    cases_processed, then `reset_cases`, flag cleared, docket 2 given again; no shift-2 ledger on that path); pass → promotion scene →
    `end_shift` (shift-2 ledger) → `set_rank 2`.

## Art (build agent) — M1 asset build
- **Added optional IDs** `wall_kerb_door_x/_y` (64×80, origin [32,64]): low gateway for `D` cells on the near kerb row/column. The full-storey `wall_door_*` on the near side hides actors behind it. Engine may use these for near-side doors. If it does not, `wall_door_*` still works.
- **Extra IDs (harmless):** `floor_flag_edge_0..1`, `desk_clerk_tray1/2`.
- `banner_red` is a **wall-hung** banner (32×64, origin [16,72]) on a bracket at the cell's near corner, because Content places it on wall cells. It works on both `_x` and `_y` walls. It is not solid.
- Soul character sheets have **75 % alpha baked in** (`"alpha_baked":0.75` in the manifest). Engine must not apply it again.
- Footprint sprites (`statue_first_clerk` 2×2, `decal_inlay_ring` 4×4) have their origin at the **footprint centre**. Engine must place them at the centre of the footprint, not at the centre of the first cell listed (Content lists decal cell [5,5] with footprint [4,4]).
- Post-process applies the ambient tint with exposure gain 1.45 (PROJECT §7.4 says plain multiply; plain multiply was too dark to read).
- Walls are 0.25-BU slabs on the **near** edge of their cell, so actors in row/column 1 stand against the face.

## 2026-11-11 — Engine

1. Engine reads Content's nested config (`clock.costs`, `queue.*`, `order.*`, `pay.*`, `promotion.*`, `judgement.composure`,
   `player.*`) via an alias table in `autoload/content.gd`; flat keys still work. Base pay comes from `ranks.json` `base_pay`.
2. `case_scored` is emitted when the audit slip is dismissed (after the soul leaves), not at the stamp; stats/autosave happen at the stamp.
   Stamped-but-unpresented cases are kept in the save (`pending_scored`) and flushed on Continue.
3. Favour/conscience are NOT computed by the engine (Content #4); `reopen_case` reverts the verdict effects' favour/conscience adds.
4. Extra engine-only ops accepted (never required): conditions `all`; effects `set_stat`, `clear_flag`; any effect may carry `conditions`.

### Integration issues
- `dlg_marrow_first` n3 says "God and the Devil", against PROJECT §5 language rule (in-fiction text uses Principal/Counterparty only).

## Orchestrator — living world (2026-11-11, owner request)
- New optional area key `"ambient"` (see header of `game/world/ambient_life.gd`): wandering `staff`, soul `flows`
  (`pass` = walk A→B and fade; `judged` = walk to a free desk seat, wait, exit by a Gilt/Ember soul door), `desk_clerks`, `max_walkers`.
  Presentation only — never touches Sim counters, GameState, clock or saves.
- Every `desk_clerk` prop not claimed by an object (`desk` / `desk_player`) automatically gets a working clerk at (x, y−1) and a soul seat at (x, y+1).
- `area_booths` enlarged 14×8 → 26×14 (9 extra desks) and `area_records_annexe` 10×8 → 16×8 (2 reading desks). All original cells keep
  their coordinates; new legend char `w` = floor where a desk clerk stands.
