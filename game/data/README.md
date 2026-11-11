# game/data — authoring guide

All content is JSON. Run `python3 tools/validate_content.py --tests` after every change; it must print `OK`.
Specs: `docs/PROJECT.md` §3, §8.5, §9.7, §10; seams: `docs/CONTRACTS.md` §2–§3 plus `docs/CONTRACT_CHANGES.md`.

| Path | What |
|---|---|
| `cases/case_s00N.json` | Soul cases (PROJECT §8.5). S-005/S-006 are `min_rank: 2` (M2). |
| `areas/area_*.json` | Rooms: ASCII `grid` (row = cy, column = cx) + `legend`, `windows`, `decor`, `objects`, `spawns`, `zones`. |
| `npcs/npc_*.json` | NPCs. `dialogue` = ordered list; the **first** entry whose `conditions` pass is used. Keep the last one unconditional. |
| `dialogue/dlg_*.json` | Node graphs: `start`, `nodes{id: {speaker, text, next \| choices, effects?, conditions? + else}}`. |
| `triggers.json` | Flow glue: `{id, on, match, conditions, effects, once}` on EventBus signals. |
| `objectives.json` | `{obj_id: {text ≤ 40, target{area, object}}}`. |
| `config.json` | Every tunable number (clock costs, queue, Order, pay, scoring, gate, dockets, incidents, ledger notes). |
| `ranks.json` | Stats (with start values) and ranks. Ranks are set by `set_rank` only (`auto:false`). |

## Text budgets (validator-enforced)
Record/archive/fact/answer card ≤ 80 chars · dialogue box ≤ 140 · answer ≤ 3 boxes · epilogue ≤ 2 boxes · archive doc ≤ 3 cards ·
≤ 4 questions · ≤ 4 choices · objective ≤ 40 · card title ≤ 3 words. Split long lines into more nodes/boxes, never shrink the font.

## Writing a case
1. Entries `r1..rn` (`tag` virtue/sin/neutral, `weight` −3..+3, sign must match tag, `ink` black/violet). Hidden entries `h1..hn`.
2. Archive docs `arc_<nnn>[a-z]` with 1–3 facsimile cards; `requires` gates a doc behind a lead (e.g. `discovered`).
3. Discoveries `d_<word>`: `triggers` (`link:[entry, arc]` | `archive: arc` | `question: q`), `ops` (`void` | `reweight` | `reveal`),
   `fact{text, side}` (side = sign of the ops' tally change), `key`. Optional `effects` (e.g. set a story flag).
4. Questions `q1..`: `general` (−1 Composure, +10 min) or `confront` (needs `requires`, +5 min). `answer` boxes, an 80-char `card`,
   optional `fact{id, text, side, key}`. 1–3 key facts per case in total.
5. `expected{tally_filed, tally_corrected, guideline}` — the validator recomputes them; G is the Rubric on the fully corrected record.
6. Ambiguous cases need ≥ 2 facts per side. Every key fact must be reachable with zero wrong links inside 3 Composure.
7. `verdicts.<side>.effects` carry the hidden stats: `favour_gilt`/`favour_ember` +1; `conscience` +1 for Heaven against G
   (or ambiguous Heaven), −1 for Hell against G (or ambiguous Hell).

## Ops
Only the condition/effect ops in CONTRACTS §3.1–3.2 (`tools/schemas/ops.json`). Every flag read in a condition must be set somewhere.
`$active_case` may stand for any case id.

## Flow at a glance (PROJECT §10.5)
New game card → Registrar → Marrow (docket 1, tutorial lines by case progress) → Registrar `call_soul` → desk → Marrow between
cases → incident after S-002 (Grist resolves it before the S-003 verdict) → Marrow closes shift 1 (`end_shift`, ledger) → Day 2 card
→ Marrow docket 2 → S-004, S-007, S-008 → gate triggers on `case_scored(case_s008)`: Pell correction / "Docket reissued" / promotion
scene (`flag_tarrow_file`) → shift-2 ledger → `set_rank 2` → stair → Adjudicator's Chamber title card → `end_prototype`.
Key flags: `flag_shift1_started`, `flag_shift1_closed`, `flag_shift2_started`, `flag_incident_active`, `flag_found_violet_ink`,
`flag_correction_pending`, `flag_gate_passed`, `flag_gate_reissue`, `flag_promotion_done`, `flag_promoted`, `flag_tarrow_file`.

## Tone
Dry bureaucratic satire on the surface, real moral weight underneath; the joke is the paperwork, never the soul. Rated 18+ (D3).
"God", "the Devil", "angel", "demon" are allowed (D4), best paired with civil-service titles ("Seraph-Grade Assessor, Third Choir",
"Demon Second Class (Debt Recovery)"); the Principal and the Counterparty remain the formal titles.

## Scoring oracle
`tools/scoring_ref.py` is the pure-Python reference for PROJECT §3.2 scoring, the §4 gate and the §6 Order/pay formulas; its tests
reproduce every §3.3 row and the §10.8 playthroughs from these files. Engine's GDScript scoring must match it.
