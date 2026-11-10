# 01 — Game Director / Systems Design Proposal

Author: Agent 1 (Director & Systems). Scope: vision, loops, judgement mechanic, rank progression, system balance, first playable, roadmap.
Out of scope (owned by others): case/lore writing, art pipeline, engine architecture, screen layouts, management-sim formulas.

## 1. Vision

**"You walk the paperwork."** A career RPG about a clerk in the afterlife's border fortress. Every decision is made standing somewhere, facing someone.

| Pillar | Meaning | Test we apply to every feature |
|---|---|---|
| P1. Places act, menus inform | Bottom-bar screens (Map/Staff/Reports/Upgrades) are the player's **notebook**: read-only, plus "set waypoint". Every state change happens at a location or to a person. | "Where do I stand and who do I face to do this?" No answer = cut or redesign. |
| P2. Judgement is reasoning, not guessing | The player is scored on what they found and how they justified it, not on matching a hidden answer in grey cases. | Can a careful player explain why they lost points? |
| P3. Rank changes the verbs | Each promotion adds a new kind of action and a new wing, not bigger numbers. | Does rank N play differently from rank N-1 in the first 5 minutes? |
| P4. The fortress remembers | Souls, staff and factions reappear changed by earlier verdicts. | Every 4th case (approx.) has an authored "echo". |
| P5. Phone-shaped | One shift = 6–10 min, interruption-safe, one thumb, no real-time fail timers. | Can I stop mid-case and resume with no loss? |

## 2. Core loops

| Loop | Length | Steps | Reward |
|---|---|---|---|
| Minute | 30–90 s | Walk to a place → talk/inspect → gain one **fact** → use it (flag, ask, cite) | New fact, new dialogue line, door opens |
| Case | 2–4 min | Collect soul → fetch ledger → interview at desk → verdict + ground → soul exits through a physical door | Merit, audit slip, faction shift |
| Shift (session) | 6–10 min | Take docket from superior → 2–4 cases → one fortress incident (gossip, favour, dispute) → report back | Wage, Order change, story beat |
| Career | 1–3 h per rank | Fill promotion requirements → promotion ceremony → new wing + new verb | New rank, location, mechanic |
| Campaign | 12–15 h target | The administrative crisis escalates across all 5 ranks | Ending shaped by doctrine + faction state |

**Time model:** the fortress clock advances per action (walk leg, question, verdict), not in real time. Pressure comes from docket size and backlog per day, never from a ticking countdown.

## 3. Soul judgement — the central mechanic

### 3.1 Evidence sources (each is a place)

| Evidence | Where obtained | From whom | Content |
|---|---|---|---|
| Declaration | Arrival Hall | Receptionist + the soul | 3–5 claims the soul makes about its own life |
| Life Ledger | Records Department | Archivist | 4–7 dated entries; the official record (can itself be wrong or tampered from rank 2) |
| Testimony | Judgement desk / chamber | The soul | Answers to questions; some questions only unlock after a flag |
| Addendum | Records, second trip | Archivist | Extra page unlocked by a lead from testimony |
| Witness (rank 2+) | Summoned to chamber | Another soul / staff | Corroborates or contradicts |
| Seized effects (rank 3+) | Border Guard HQ | Guard captain | Objects, contraband writs, forged ledgers |

### 3.2 Player actions inside a case

| Action | Rule | Cost |
|---|---|---|
| Flag discrepancy | Tap one claim + one ledger entry. If the pair is an authored contradiction → becomes a **fact**. | Wrong flag: −1 Composure |
| Ask question | Pick from 3–5 available; flagged discrepancies add questions. | −1 Composure each |
| Composure | Soul has 3 pips (rank 1). At 0 the interview ends. Forces prioritising. | — |
| Cite ground | On the verdict form choose 1 discovered fact as the ground (2 from rank 2). | — |
| Verdict | Stamp. Soul walks out through the gold or red door. | Irreversible (appeals from rank 2) |

### 3.3 Verdict options by rank

| Rank | Verdicts available |
|---|---|
| 1 | Heaven, Hell |
| 2 | + **Remand to Purgatory** (occupies one of a limited number of cells at Border Guard HQ; must be resolved later), + hear **Appeals** |
| 3 | + **Refer** to a subordinate / escalate to superior (delegation has competence and corruption risk) |
| 4 | + **Negotiated transfer** (trade a disputed soul with an envoy for a concession) |
| 5 | + **Doctrine edit** (change a Codex rule; all later "clear" cases are judged by the new rule) |

### 3.4 How "correctness" is scored

Every case has a hidden **type**. The Codex is a short, in-world rule list (8–12 rules, readable on the booth wall).

| Type | Definition | Verdict scoring |
|---|---|---|
| Clear | Codex + full facts give one answer | Right +4, wrong −2 and "Overturned" |
| Contested | One answer once a hidden key fact is found; the surface reading points the other way | Same as Clear |
| Ambiguous | Codex rules conflict or are silent | **Verdict never scored.** +4 if the cited ground genuinely supports the chosen side, else 0 |

Merit per case (max 9): **Diligence** 0–3 (+1 per key fact found, 3 authored per case) + **Verdict** (above) + **Grounds** +2 if the cited fact is relevant to the verdict.

Three ledgers, deliberately separate:
- **Merit** (visible) — procedure and reasoning. Drives promotion.
- **Favour: Heaven / Favour: Hell** (visible from rank 2, hinted at rank 1) — moved by where souls go, strongly by ambiguous and disputed ones. Drives politics.
- **Conscience: Mercy ↔ Rigor** (never shown as a number) — only changes how NPCs describe you and which story branches open. Never rewarded or punished mechanically.

Audit rate: rank 1 = 100% of cases; rank 2+ = roughly 1 in 3. Unaudited cases are what makes corruption and mercy-against-the-rules possible.

Case mix: R1 60/25/15 (clear/contested/ambiguous) → R2 40/30/30 → R3+ only contested, ambiguous and disputed cases reach the player; clear ones are handled by staff.

### 3.5 Consequences

| Delay | Examples |
|---|---|
| Immediate | Soul exits by gold/red door; audit slip arrives at desk; Merit/Order tick |
| Next shift | Superior's remark; a relative of a judged soul arrives as a case; faction clerk leaves a note |
| Long | Soul returns as appellant, witness, or new hire; envoy cites your record in a dispute; Order shifts the crowd density and guard presence in public spaces |

## 4. Rank progression

| # | Rank | New locations | New mechanics | Promotion gate (design intent) |
|---|---|---|---|---|
| 1 | Junior Processing Clerk | Arrival Hall, Central Court, Records reading room, Clerks' Booths | Declaration vs ledger, interview, 2 verdicts | Merit + low overturn count |
| 2 | Senior Adjudicator | Judgement Chambers (own chamber), Records deep stacks, Appeals gallery | Remand, appeals, witnesses, 2 grounds, tampered ledgers, mentoring 1 junior | Merit + resolved appeals + one "crisis" case |
| 3 | Department Supervisor | Administrative Offices, Border Guard HQ, staff quarters | Team of 6–12: desk assignment, morale, backlog, corruption audit; player judges escalations only | Dept efficiency + backlog under cap + one corruption case closed |
| 4 | Chief Commissioner of the Border | Diplomatic Quarter, Heaven Gate bridge, Hell Gate bridge, undercrofts | Multi-department budget, envoys, soul disputes, summits, investigations | Order ≥ target, both Favours above floor, summit completed |
| 5 | High Chancellor of Purgatory | High Chancellor's Office, audience halls of Heaven and Hell | Doctrine edits, audiences with God and the Devil, crisis endgame | Ending |

### Activity balance (% of play time)

| Rank | Walking/exploring | Judging | Management | Politics/narrative |
|---|---|---|---|---|
| 1 | 30 | 60 | 0 | 10 |
| 2 | 30 | 50 | 10 | 10 |
| 3 | 30 | 25 | 35 | 10 |
| 4 | 30 | 15 | 25 | 30 |
| 5 | 25 | 10 | 20 | 45 |

Walking stays near 30% at all ranks. Rules: no walk leg over 25 s without something to see, overhear or pick up; shortcuts (keys, lifts, bridges) are rank rewards, not menu fast-travel; judging never disappears — the hardest cases always reach the player.

## 5. Anti-menu anchoring

| System | Place | Person | Physical action |
|---|---|---|---|
| Receive work | Superior's lectern/office | Direct superior | Walk up, take docket |
| Collect soul | Arrival Hall queue | Receptionist | Call next; soul follows the player |
| Research | Records Department | Archivist | Request ledger at counter; later walk the stacks |
| Verdict | Booth / chamber | The soul | Stamp at the desk; soul leaves by a real door |
| Remand | Border Guard HQ cells | Guard captain | Escort or hand over; visit to re-interview |
| Hire / dismiss / reassign | The employee's own desk, or the Duty Roster board in Admin Offices | The employee | Talk to them; they visibly move desk |
| Morale / disputes | Where the staff are | Both parties | Mediate in person |
| Budget | Treasury counter in Admin Offices | Treasurer | Sign the allocation ledger |
| Corruption | Suspect's desk, Records, Guard HQ | Auditor, suspect | Gather evidence as in a soul case, then confront |
| Diplomacy | Diplomatic Quarter | Envoys | Attend in person; walk between delegations |
| Upgrades | The room being upgraded | Works foreman | Commission on site; room visibly changes |

Convenience at high rank is diegetic: a **runner** NPC can carry an order for you — it takes clock time and you can see them walk it.

## 6. First playable prototype (10–15 min)

**Goal:** prove walk → collect → research → interview → verdict → promotion is fun on a phone. Nothing else.

### 6.1 Rooms (one small hub-and-spoke block; every leg 10–15 s)

| Room | Function | Contents |
|---|---|---|
| Central Court | Hub; statue; three exits + one locked stair | 1 guard at the red-carpet stair (locked), 4–6 ambient walkers |
| Arrival Hall | Collect souls | Receptionist desk, queue of 8–10 idle souls |
| Records reading room | Fetch ledgers | Archivist counter, shelves (decor) |
| Clerks' Booth | Judge | Player desk, soul's stool, gold door, red door, Codex plaque (4 rules), supervisor's lectern, 1 colleague at next desk |
| Adjudicator's Chamber | Promotion reward, end of prototype | Larger desk, window to both skies; reached via the unlocked stair |

### 6.2 NPCs (5 named + souls)

| NPC | Place | Role in prototype |
|---|---|---|
| Supervisor | Booth lectern | Gives docket, delivers audit summary, promotes |
| Receptionist | Arrival Hall | Hands over next soul + Declaration |
| Archivist | Records | Hands over Ledger; Addendum on request |
| Fellow clerk | Booth | Tutorial hints, one piece of gossip between shifts |
| Stair guard | Court | Blocks the stair until promoted, then salutes |
| 6 souls | Queue | 5 core cases + 1 remedial |

### 6.3 Cases (structure only; content from Narrative)

| # | Shift | Type | Key facts | Teaches |
|---|---|---|---|---|
| 1 | 1 | Clear | 1 (ledger pre-attached, no Records trip) | Walk, collect, stamp, door |
| 2 | 1 | Clear | 3 | Fetch ledger; flag a discrepancy |
| 3 | 2 | Contested | 3 | A flag unlocks the question that reverses the surface reading |
| 4 | 2 | Clear | 3 | Composure limits: cannot ask everything |
| 5 | 2 | Ambiguous | 3 | Addendum trip; Codex rules conflict; grounds matter, verdict does not |
| 6 | remedial | Clear | 3 | Only offered if promotion check fails |

### 6.4 Exact judgement flow

1. Talk to Supervisor at lectern → docket (shift 1: cases 1–2; shift 2: cases 3–5). Objective card updates.
2. Walk to Arrival Hall → talk to Receptionist → "Call next" → soul leaves queue and **follows the player**; Declaration added to case file.
3. Walk to Records → talk to Archivist → Ledger added (skipped for case 1).
4. Walk to Booth → tap own desk → soul sits → case view opens (Declaration left, Ledger right, soul portrait + 3 Composure pips).
5. Flag: tap a claim, then a ledger entry. Correct pair → fact recorded, new question appears. Wrong pair → −1 Composure.
6. Ask: choose questions (−1 Composure each). Answers may reveal facts. Case 5: one answer unlocks "Request Addendum" → optional walk to Records and back (case state persists; soul waits on the stool).
7. Tap "Proceed to verdict" (available any time) → choose **Heaven** or **Hell** → choose 1 ground from recorded facts (or "No ground") → stamp.
8. Soul stands and walks out the gold or red door. Audit slip appears on the desk: Diligence x/3, Verdict (Upheld / Overturned / Noted), Grounds (Sound / Unsound), Merit gained.
9. Repeat 2–8. After the last case of the shift, report to Supervisor → shift summary. Between shifts the fellow clerk has one new line and the day clock rolls.
10. After case 5 → promotion check (6.6).

### 6.5 Stats tracked

| Stat | Start | Change | Shown |
|---|---|---|---|
| Souls processed | 0/5 | +1 per verdict | HUD |
| Merit | 0 | 0–9 per case (3.4) | Objective card "Merit n/28" |
| Overturned | 0 | +1 per wrong verdict on Clear/Contested | Shift summary |
| Order % | 60 | +2 upheld, −6 overturned, 0 ambiguous | HUD |
| Coin | 0 | +10 wage per case; no sink yet | HUD |
| Favour Heaven / Hell | 0 / 0 | +1 to receiving side; ±2 on case 5 | Hidden; one closing line from Supervisor reflects it |
| Conscience | 0 | −1 Rigor / +1 Mercy on cases 3 and 5 | Hidden; logged for later use |
| Day / time | Day 1 08:00 | +5 min per walk leg, +10 per question, +20 per verdict | HUD |

### 6.6 Promotion: Junior Processing Clerk → Senior Adjudicator

| Condition | Threshold |
|---|---|
| Cases processed | 5 of 5 |
| Merit | ≥ 28 of 45 (62%) |
| Overturned verdicts | ≤ 1 of the 4 scorable cases |

- **Pass:** Supervisor hands over the key → stair guard steps aside → player walks up to the Adjudicator's Chamber → title card "Senior Adjudicator" → end of prototype.
- **Fail:** Supervisor assigns remedial case 6 (max +9). Re-check with Merit ≥ 28 and Overturned ≤ 2. Still failing → "Docket reissued": restart from shift 2 with Merit and Overturned reset to their end-of-shift-1 values.
- Reference outcomes: careless (no flags, guessed verdicts) ≈ 10–18 Merit → fail; attentive ≈ 32–40 → pass; perfect = 45.

### 6.7 Explicitly out of the prototype

Staff management, budget, upgrades, remand, appeals, witnesses, Diplomatic Quarter, Border Guard, save slots (single autosave only), audio beyond ambience + stamp, procedural cases, Map/Staff/Reports/Upgrades screens (buttons may be present but disabled).

## 7. Roadmap after prototype

| Milestone | Content | Exit criterion |
|---|---|---|
| M1 First playable | Section 6 | Fresh players finish in 10–15 min and can explain why they lost Merit |
| M2 Rank 2 vertical slice | Own chamber, Remand, appeals, witnesses, 2 grounds, tampered ledger, 15 cases, first echo cases, Reports notebook screen | 45–60 min; rank 1→2→gate of 3 |
| M3 Case pipeline | Data-driven case format, authoring/validation tool, 40+ cases, semi-procedural filler cases for clear type | A new case added without code changes; validator catches unreachable facts |
| M4 Rank 3 management | Admin Offices, Border Guard HQ, 8–12 staff with traits, morale/backlog/corruption, Duty Roster, Staff notebook screen | Management done entirely on foot; no action-bearing menu |
| M5 Rank 4 politics | Diplomatic Quarter, gates, envoys, disputes, one summit, budget, crisis act 2 | Favour state visibly changes fortress and dialogue |
| M6 Rank 5 + endgame + ship | Chancellor's Office, doctrine edits, audiences, endings, balancing, mobile performance, store builds | Full campaign 12–15 h on mid-range Android |

## Dependencies on other roles

| Role | What I need |
|---|---|
| World/Narrative | 6 prototype cases written to the 6.3 structure (claims, ledger entries, 3 key facts, questions, valid grounds, type); the 4-rule prototype Codex and the 8–12 rule full Codex; names/voices for the 5 NPCs; crisis arc beats mapped onto the 5 rank gates; echo pairings |
| Environment/Art | The 5 rooms of 6.1 with clearly readable gold and red exit doors; follower-soul sprite; queue of idle souls; locked/unlocked stair states; confirmation that a 10–15 s leg between rooms fits the tile scale |
| Technical | Case data schema that supports facts, flag pairs, gated questions and persistent mid-case state; NPC follow behaviour; action-driven clock; autosave on room transition; confirmation that 5 rooms + ~20 animated characters hold frame rate on target phones |
| UI/UX Mobile | One-thumb case view (two documents + portrait + pips) on a 6" portrait or landscape screen — orientation decision; pair-tap flagging interaction; audit slip presentation; "notebook = read-only" convention for bottom-bar screens; movement control scheme |
| Management/Sim | Formulas for morale, competence, backlog, corruption that take **in-person actions** as inputs (section 5); how Order % is computed fortress-wide from rank 3; confirm Coin sinks so the HUD stat has meaning by M2 |
| QA/Producer | Playtest of M1 against the exit criterion; arbitration if any proposal introduces an action-bearing menu (violates P1); check the 28/45 threshold against real play data |

## Open questions / risks

1. **Repetition of the fetch route.** Five trips over the same three legs may feel rote. Mitigation: case 1 skips Records, case 5 adds an Addendum trip, ambient lines change per shift. If still dull in playtest, batch two souls per trip.
2. **Pair-tap flagging can be brute-forced.** Composure penalty limits it (3 pips), but tuning is unverified until played.
3. **Ambiguous-case scoring depends on authored "valid grounds" lists.** If Narrative's lists feel arbitrary, P2 fails. Each ambiguous case needs at least 2 valid grounds per side.
4. **Thresholds are estimates.** 28/45 and the Order deltas are untested; the reference outcomes in 6.6 are reasoned, not measured.
5. **HUD interpretation.** I read the mockup's three stats as Souls / Coin / Order. Coin has no sink in the prototype; needs Management/Sim to confirm its purpose or it should be hidden until M2.
6. **Orientation.** The mockup is landscape; the two-document case view favours landscape. Needs UI/UX decision before M1 build.
7. **"Places act" vs late-game convenience.** At rank 4–5 the fortress is large; runners and shortcuts must be enough or players will demand menus. Needs a walk-time budget from Art/Technical once the map scale is known.
8. **Scope of 12–15 h campaign** implies roughly 150+ authored cases; M3's pipeline and filler-case approach is the main lever and is unproven.
9. **Hidden Conscience stat** risks feeling like invisible judgement of the player; must surface only through NPC tone, never as a penalty.
