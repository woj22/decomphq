# 06 — Management & Simulation Proposal

**Role:** Management and Simulation Designer. **Scope:** the fortress as a running system underneath the Director's core loop.
**Principle:** the fortress is a pipeline of integers that is always ticking; the player's rank decides how much of it they can see and touch. Every number here is a starting value for tuning and should live in one data file.

## 1. Clock
| Item | Value |
|---|---|
| Playable shift | 08:00–18:00 (10 game hours) |
| Time scale | 1 game minute = 1 real second, so one shift = 10 real minutes |
| Sim tick | every 10 game minutes (60 ticks per shift) |
| Clock pauses | story dialogue, pause menu, tutorial cards. It does **not** pause at the judgement desk (time pressure) |
| Night (18:00–08:00) | resolved as one step at shift end: arrivals at 0.3 x rate, every department at 0.3 x capacity |
| Day roll-over | pay, morale/integrity update, event draw, favour update, autosave. No offline progress |

Arrival rate: `λ(day, t) = 12 souls/h x (1 + 0.02 x (day − 1)) x wave(t) x eventMult`
`wave`: 08–10 = 1.3, 10–14 = 1.0, 14–16 = 0.7, 16–18 = 1.0. `eventMult` = 1, or 1.5–2.5 on story surge days (war, plague). The 2 %/day growth is the brief's "administrative crisis" expressed as a number.

## 2. Soul pipeline
`Arrival -> Registration -> Records lookup -> [30 % flagged: Investigation] -> Judgement -> Transport -> Heaven / Hell`; contested verdicts go to **Appeals**, and holds, escapees and pending appeals sit in **Detention**.

| Stage (location) | Role | Base rate, souls per staff-hour | Staff, Day 1 | Queue cap | Day-1 queue |
|---|---|---|---|---|---|
| Registration (Arrival Hall) | receptionist | 3.0 | 5 | 80 | 46 |
| Records lookup (Records Dept) | archivist | 2.0 | 7 | 40 | 22 |
| Investigation (Judgement Chambers, lower) | investigator | 0.5 | 8 | 20 | 10 |
| Judgement (Judgement Chambers) | adjudicator | 1.0 | 12 + player | 50 | 28 |
| Transport (Heaven Stair / Hell Ferry) | transporter | 2.5 | 5 | 30 | 8 |
| Appeals (R2+) | senior adjudicator | 0.4 | 2 | 20 | 6 |
| Detention (Border Guard HQ) | guard | holding only, cap 20 | 10 | 20 | 4 |
| Oversight | auditor 2, supervisor 4 | — | 6 | — | — |
| **Total** | | | **55 + player** | | **124** |

Per tick, per department `d` (Δt = 1/6 h):

`Out_d = min( Q_d , Present_d x BaseRate_d x Eff_d x Δt , Cap_next − Q_next )`

The third term is blocking: a full downstream hall stops the upstream one, and the overflow stands visibly in corridors and courtyards. Fractions carry over in an accumulator, so the run is deterministic for a given seed.

**Department efficiency**
`Eff_d = CompMod x MoraleMod x SupMod x ToolMod x (1 − Disruption)`

| Term | Formula | Neutral point |
|---|---|---|
| CompMod | `0.5 + C̄/100` | C̄ = 50 gives 1.0 |
| MoraleMod | `0.6 + M̄/150` | M̄ = 60 gives 1.0 |
| SupMod | `1 + 0.15 x (SupC − 50)/50 − 0.02 x max(0, staff/supervisors − 12)` | SupC = 50, span 12 or fewer |
| ToolMod | `1 + Σ upgrade bonuses` (each +0.05 to +0.15) | 1.0 |
| Disruption | `0.05 x open disputes + absent fraction + 0.10 if a realm inspector is posted` | 0 |

**Quality**
`Err_d = clamp( 0.20 − 0.15 x C̄/100 + 0.05 x max(0, Load_d − 1) + 0.30 x Corr_d , 0.02 , 0.60 )`, where `Load_d = Q_d / (4 x hourly capacity)`.

- Wrong verdicts: `Judged x Err_judgement`. Appeals lodged = 20 % of wrong + 2 % of right. Appealed souls wait in Detention.
- Records and Investigation errors do not make wrong verdicts directly; they raise the next stage's Err by half their own. Bad files make bad judgements, which is the hook for "find inconsistencies".
- Wrong deliveries are only discovered by auditors (each auditor samples 10 dispatched souls per day). Discovered ones cost favour.

## 3. Employees
Every employee is a stored record: seeded name, role, grade (1–3), four stats 0–100, 1–2 traits, 0–1 secret, flags.

| Stat | Generated | Drives |
|---|---|---|
| Competence C | N(50, 15); +0.2/day on the job | speed (CompMod), Err |
| Morale M | starts 60 | speed (MoraleMod), burnout, quitting |
| Integrity I | N(60, 20) | bribe resistance; reporting others |
| Ambition A | N(45, 20) | promotion requests, rivalry, defection to a realm |

**Daily morale update:** `ΔM = 0.1 x (Target − M) − 3 x clamp(Load_d − 1, 0, 2) + WageMod + EventMods`
Target 60 (68 with Refectory). WageMod: paid 110 % = +2, 100 % = 0, cut or late = −6. Overtime order = −4 (and +20 % capacity that day). Personal praise from the player = +5 once per 3 days. Open dispute = −2/day to both parties.

**Daily bribe roll (per employee):** `p = 0.03 x (1 − I/100) x (1 + max(0, 60 − M)/60)`, doubled for Greedy. Success sets `on_take`. `Corr_d = on_take staff / staff`. Each auditor-day assigned to a department exposes one on-take employee with 40 % chance, which opens a Bribery event. Corrupt adjudicators also skew the Heaven/Hell share toward their paymaster by 10 points each (see quotas in section 4).

| Trait | Effect | Trait | Effect |
|---|---|---|---|
| Meticulous | Err −30 %, speed −10 % | Brisk | speed +15 %, Err +25 % |
| Pious / Cynic | verdict lean ±5 points to Heaven / Hell | Zealot | I +20, starts disputes x2 |
| Mentor | desk neighbours +0.5 C/day | Gossip | reveals one colleague's secret per 5 talks |
| Greedy | bribe roll x2 | Loyal | never quits, never defects |
| Clock-watcher | leaves 17:00 | Night owl | works the night step at full rate |

Secrets (about 20 % of staff, found by talking, gossip, audits or documents in the world): on Hell's payroll; Heaven's informant; forged credentials (shown C is real C + 20); soul smuggler; escaped detainee posing as staff; gambling debts (bribe roll x3). Each secret gives a choice: expose, protect or exploit, with meter consequences. Content belongs to Narrative.

| Event | Trigger | In-world resolution (walk to the people involved) | Outcomes |
|---|---|---|---|
| Dispute | 2 staff, same room, trait clash, or M̄ < 45; about 1 per 20 staff per 5 days | hear both, rule, or transfer one | Disruption cleared; loser M −8; ignored 3 days leads to one quitting |
| Bribery | on_take exposed, or offered to the player | confront, report to auditor, take a cut | dismiss (Order +2), cover (Corr stays, leverage gained), share (purse up, own Integrity flag) |
| Burnout | M < 25 for 3 days | grant leave, reassign, ignore | absent 3 days / 30 % quits / collapses at desk in view |
| Promotion request | A > 70 and 10+ days in grade | answer at their desk | grant: wage x1.25, grade +1; deny: M −10, I −5, A-driven rivalry |

Budget: 1–3 events drawn per day, at most 6 live at once.

## 4. Economy
Single currency: **obols** (ob). Favour is a meter, not a currency, and cannot be bought directly.

| Income per day | Formula | Day-1 value |
|---|---|---|
| Conveyance fee | 4 ob x souls delivered (paid by the receiving realm) | about 500 |
| Heaven stipend | `250 x HF/50`, capped 500; 0 while HF < 25 | 250 |
| Hell stipend | `250 x LF/50`, capped 500; 0 while LF < 25 | 250 |
| Special grants | negotiated in the Diplomatic Quarter (R4+), tied to a pledge | 0 |

Daily wages (ob): receptionist 8, transporter 8, archivist 10, guard 10, investigator 12, adjudicator 14, auditor 16, supervisor 24. Grade multiplier x1.0 / x1.25 / x1.5. Day-1 wage bill 670 ob. Upkeep 40 ob per open wing (5 open = 200). Hire fee = 5 days' wage. Dismissal = 3 days' severance, and M −3 in that department. Treasury starts at **2,750 ob**; a negative treasury means wages are late (WageMod −6) and building stops.

**Quotas** (reissued every 5 days, posted on the Diplomatic Quarter noticeboard):
- Throughput: at least 110 souls dispatched per day (rises with λ).
- Share bands: Heaven expects 35–55 % of dispatches; Hell expects 45–65 %. Both are satisfied at 45–55 % Heaven. As the story crisis advances the bands drift apart until they no longer overlap, at which point pleasing both is impossible and the choice becomes political.

## 5. Global meters
| Meter | Range / start | Computation |
|---|---|---|
| **Backlog B** | integer, start 124 | sum of all queues. `BacklogDays = B / (bottleneck hourly capacity x 10)` |
| **Order** | 0–100 %, start 68 | moves 10 % of the gap per hour toward `100 − 12 x min(BacklogDays, 3) − 60 x Corr − 15 x (1 − GuardCover) − 4 x OpenIncidents`, with `GuardCover = min(1, guards / (B/12))` |
| **Heaven favour HF** | 0–100, start 50 | daily: +1 quota met; −2 share outside its band; −0.5 per discovered wrong delivery; −1 if BacklogDays > 2; plus diplomacy and events |
| **Hell favour LF** | 0–100, start 50 | same rules against Hell's band |

Day-1 check: BacklogDays 124/122 = 1.02; Corr 0.12; GuardCover 10/10.3 = 0.97; 3 open incidents. Target = 100 − 12.2 − 7.2 − 0.5 − 12 = **68**.

| State | Condition | Effect (always shown in the world first, then on the HUD) |
|---|---|---|
| Strained | BacklogDays 1–2 | queues spill into courtyards; M −1/day everywhere |
| Critical | BacklogDays 2–3 | souls wander; Order target −8 extra; both favours −1/day |
| Gates Sealed | BacklogDays > 3 for 3 days | realm inspectors take over for 2 days: treasury −25 %, both favours −15, rank review. A setback, not a game over |
| Unrest | Order < 40 | queue scuffles; guards pulled from desks; all Eff x0.85 |
| Breach | Order < 20 | souls cross the wrong border; both favours −5/day; Detention fills |
| Cold shoulder | a favour < 25 | that stipend frozen; inspector posted in one department (Disruption +0.10) |
| Embargo | a favour < 10 | that realm's gate closed for a day; Transport blocks and backs up |
| Patronage / Partisan | a favour > 75 / abs(HF − LF) > 40 | stipend at cap and one gift upgrade, other favour −1/day / the scorned realm opens Soul Dispute events against past verdicts |

## 6. Fortress expansion
| Build | Unlock | Cost / days | Simulation effect | Visible change |
|---|---|---|---|---|
| Second Registration Arcade | R3 | 600 / 2 | +4 receptionist desks; Arrival cap +60 | new rope lanes and lantern row; portcullis raised |
| Records Undercroft | R3 | 900 / 3 | +6 archivist desks; Records ToolMod +0.10 | stair opens; lit shelf stacks below the floor grate |
| Appeals Court | R2 story, R4 expand | 1,200 / 4 | Appeals bench +4; appeal rate −25 % | sealed doors open; gallery fills with petitioners |
| Detention Tower | R4 | 1,000 / 3 | Detention cap 20 to 60; Breach effects halved | tower rises over Border Guard HQ; lit cell windows |
| Stair / Ferry enlargement (two builds) | R4 | 800 / 3 each | that realm's transport +50 % | wider golden stair / second ferry at the red quay |
| Refectory and Dormitory | R4 | 700 / 2 | morale Target 60 to 68 | staff eat and rest there off-shift; chimney smoke |
| Audit Office | R4 | 900 / 3 | +4 auditor desks; exposure chance 40 % to 60 % | ledger hall; auditors seen walking the departments |
| High Chancellor's Office | R5 | story | edicts; summons bell | tower top opens; fortress-wide view |

Construction is physical: scaffolding and mason NPCs occupy the site for the build days, the area is walkable but roped off, and completion adds desks which then need hiring to fill. Staff headcount grows roughly 55 (R1), 80 (R2), 130 (R3), 250 (R4), 400+ (R5).

## 7. Running it cheaply on mobile
| Tier | What | Count | Update cost |
|---|---|---|---|
| A. Department aggregates | queue, present staff, C̄, M̄, Ī, Corr, Eff | 8–12 records | a few multiplications each per tick (every 10 real seconds) |
| B. Employee roster | one small record per employee (stats, traits, secret, flags) | 55 to 400+ | touched **once per game day** (morale, bribe roll, growth); aggregates are recomputed from the roster at roll-over |
| C. Embodied NPCs | pathing, animation, dialogue | up to about 30, only in the player's room and adjoining ones | per frame; named staff and live event actors get priority |
| D. Crowd | soul queues and distant clerks | instanced sprites | no logic; positions derived from integers |

- A queue is an integer. The Arrival Hall draws `min(Q, visible slots)` soul sprites along the lane path; when Q drops, the front sprite walks off and the rest shuffle. Overflow beyond the slots is drawn as a clump at the gate, and beyond that as density tiers (sparse, packed, spilling).
- Only souls that reach the **player's** desk or the Appeals bench become full cases. All others are counts with a Heaven/Hell/contested split.
- Embodied NPCs are drawn from the room's roster when the player enters and return to roster rows on leaving; an event promotes its 1–3 actors to Tier C wherever they are, so the argument is really happening at those desks.
- Everything is seeded and deterministic, so save data is the aggregates, the roster and the seed.

## 8. Every action happens in the world
| Action | Where / who |
|---|---|
| Read state | each department's slate **noticeboard** (queue, staff present, errors) and its supervisor's morning report; Exchequer ledger (treasury); Diplomatic Quarter board (quotas, favour); courtyard tally board (Backlog) |
| Judge / hear an appeal | sit at your desk / the Appeals bench |
| Praise, warn, question, settle a dispute, answer a promotion request | talk to the employee at their desk |
| Reassign | talk to the employee, issue a transfer slip; they walk to the new desk |
| Dismiss | in person, or via their supervisor (slower, M −1 extra) |
| Hire | Hiring Hall bench in the Administrative Offices: candidates physically wait; talk to each, one visible stat is hidden until interviewed |
| Set wages, approve overtime; assign auditors | Paymaster's desk, Exchequer; Chief Auditor's desk |
| Build / upgrade | Master Mason's drafting table in the courtyard, then visit the site |
| Set department policy (Speed vs Care, Strict vs Lenient) | tell that supervisor |
| Negotiate grants, quotas, bands | envoys in the Diplomatic Quarter |

Walking is kept tolerable by in-world shortcuts earned with rank, not by menus: **runners** (R3: hand a slip to a runner; it arrives after real transit time), **speaking tubes** in your office to each supervisor (R4), **summons bell** that brings a named person to you (R5).
The mockup's bottom bar (Staff / Reports / Upgrades) is proposed as the player's **pocket ledger**: read-only copies of what they have personally read or been told, stamped with the day and hour they saw it. It can set a waypoint to the relevant desk but cannot perform any action.

## 9. Staging by rank
| Rank | Visible | Controllable | Still ticking unseen |
|---|---|---|---|
| 1 Junior Processing Clerk | shift clock; souls waiting; own purse; Order; own processed and accuracy; the Arrival Hall queue as bodies; colleagues' moods through talk | own verdicts; whether to report or ignore what they witness | the entire pipeline, roster, events, treasury, favour. The player's desk is 1 of 13 judgement desks and its output is added to the department's |
| 2 Senior Adjudicator | Judgement Chambers noticeboard (queue, Err); Appeals and Detention; two juniors' accuracy | appeals; spot-check and overturn juniors' verdicts; route cases between 3 desks; request Records priority | other departments, money, favour |
| 3 Department Supervisor | full roster of own department (stats revealed by talking and time); neighbours' noticeboards; department budget | desks, overtime, disputes, promotions, discipline, policy, small upgrades | treasury, hiring pool, favour |
| 4 Chief Commissioner | all departments; treasury; HF, LF, quotas, bands | hire and dismiss anywhere; appoint supervisors (who then run their department by policy); auditors; wings; grants | realm-internal factions |
| 5 High Chancellor | everything, plus forecasts of λ and band drift | edicts (fortress-wide modifiers, each with a cost); negotiate bands and quotas at summits; crisis levers (seal a gate, mass amnesty) | — |

The HUD coin always shows the money the player personally controls: own purse (R1–2), department budget (R3), treasury (R4–5).

## 10. Worked example: Day 1, whole fortress (aggregate tier)
Judgement efficiency: C̄ 52 gives 1.02; M̄ 55 gives 0.967; supervisor C 55, span 12 gives 1.015; no tools; one open dispute gives 0.95. `Eff = 1.02 x 0.967 x 1.015 x 1.0 x 0.95 = 0.95`.
Hourly capacities: Registration 5 x 3.0 x 0.90 = 13.5; Records 7 x 2.0 x 0.95 = 13.3; Investigation 8 x 0.5 x 1.0 = 4.0; Judgement 12 x 1.0 x 0.95 + player 0.8 = 12.2; Transport 5 x 2.5 x 1.0 = 12.5.

| Block | Arrivals | Registration out / queue | Records out / queue | Investigation out / queue | Judgement out / queue | Dispatched / transport queue |
|---|---|---|---|---|---|---|
| Start 08:00 | — | — / 46 | — / 22 | — / 10 | — / 28 | — / 8 |
| 08–10 | 31 | 27 / 50 | 27 / 22 | 8 / 10 | 24 / 31 | 25 / 7 |
| 10–14 | 48 | 54 / 44 | 53 / 23 | 16 / 10 | 49 / 35 | 50 / 6 |
| 14–16 | 17 | 27 / 34 | 27 / 23 | 8 / 10 | 24 / 38 | 25 / 5 |
| 16–18 | 24 | 27 / 31 | 27 / 23 | 8 / 10 | 24 / 41 | 25 / 4 |
| **Day** | **120** | 135 | 134 | 40 | **121** | **125** |

- Backlog: 124 + 120 − 125 = **119** (pipeline 109, Appeals 6, Detention 4). Judgement is the bottleneck: its queue grew 28 to 41 while Registration fell 46 to 31. This is what the Rank 3 player should notice on the noticeboard.
- Quality: Err = 0.20 − 0.078 + 0 + 0.036 = 0.16, so 19 wrong verdicts. Appeals lodged 4 + 2 = 6; the bench heard 6; net 0.
- Share: 57 to Heaven, 68 to Hell = 46 % Heaven, inside both bands. Quota 110 met. HF +1, LF +1, minus 0.5 for one wrong delivery an auditor found for Heaven: HF 50.5, LF 51.
- Money: fees 125 x 4 = 500; stipends 250 + 250; income **1,000**. Wages 670 + upkeep 200 = **870**. Net **+130**; treasury 2,750 to 2,880.
- Order: one dispute settled (2 incidents left) gives target 100 − 11.7 − 7.2 − 0 − 8 = 73; the meter drifts from 68 to about **71** by 18:00.
- Night step: arrivals 0.3 x 12 x 14 = 50; bottleneck 0.3 x 12.2 x 14 = 51. Day 2 opens at B = 118 with λ = 12.24/h. With no intervention, arrivals exceed capacity from Day 3 and BacklogDays passes 2 around Day 12.

## 11. PROTOTYPE subset (10–15 minute first playable)
One shift at Rank 1. Three integers, five embodied NPCs, no roster, no treasury, no favour, no events deck.

| Element | Specification |
|---|---|
| Clock | frozen at 08:00 until the player reports to the supervisor (about 2 minutes of free walking). Then 08:00–18:00 at 1 game minute per real second = **10 minutes**. Pauses only in tutorial cards and the pause menu. Wrap-up about 1–2 minutes |
| Tick | every 5 real seconds, with fractional accumulators |
| Arrival queue `A` (Arrival Hall) | starts **16**. Grows at **3.0 souls per game hour 08–10, then 2.0** (22 over the shift). Shown as soul sprites in 4 rope lanes x 8 slots; any above 32 clump at the gate |
| Registrar NPC | moves 1 soul from `A` to the bench every 25 s while `A` > 0 and the bench is not full (2.4 per game hour) |
| Bench queue `J` (outside the chambers) | starts **8**, cap 12, shown as seated souls |
| Two NPC adjudicators | each takes 1 soul from `J` every 100 s (1.2 per game hour together, **12 per shift**); the soul visibly leaves through the gold door or the red door |
| Player desk | interacting calls the front soul of `J`. Expected 60–75 s per case, so **6–10 cases** |
| Transport | instant; counters `Heaven` and `Hell` |
| Scripted incident | 12:00: a soul ducks the rope and wanders. Telling the guard resolves it. Ignored until 14:00, it counts as unresolved |
| Objective card | "Process the incoming wave of souls (0 / 6)" |
| End of shift | bell at 18:00; the supervisor hands over a pay packet and a one-page shift report |

End-of-shift souls waiting = 24 + 22 − 12 − P: P = 0 gives 34, P = 6 gives 28, P = 8 gives 26, P = 10 gives 24. A diligent player holds the line; an idle one watches the hall fill.

**The three HUD stats**

| Icon | Name | Exact meaning in the prototype | Start |
|---|---|---|---|
| Person | **Souls waiting** | `A + J`: every soul in the fortress not yet sent on | 24 |
| Coin | **Purse** | the player's own obols; changes only at the pay packet (and one optional purchase) | 12 |
| Star with % | **Order** | `clamp(68 + 2 x Sound − 5 x Unsound − max(0, Souls − 30) + 4 x Resolved − 4 x Unresolved, 0, 100)`, displayed easing 1 point per second | 68 % |

- **Processed** = verdicts the player has stamped. **Sound** = verdict is inside the case's defensible set (defined per case by the Director and Narrative). **Unsound** = Processed − Sound. **Accuracy** = Sound / Processed. Processed and Accuracy appear on the desk blotter and the shift report, not on the HUD.
- **Pay packet** = `8 base + 1 x Processed + 1 x Sound − 2 x Unsound + 5 if Processed >= 6 + 3 if Accuracy >= 80 %`.
- Example shift: 8 processed, 6 sound, 2 unsound, incident resolved, 26 souls waiting. Accuracy 75 %. Pay = 8 + 8 + 6 − 4 + 5 = **23 ob**, purse 12 to 35. Order = 68 + 12 − 10 − 0 + 4 = **74 %**.
- Optional spend: Quartermaster's hatch sells a desk lamp for 20 ob (highlights one inconsistency per case next shift). It proves the earn-and-spend loop in one object.
- Suggested progression input for the Director: promotion review passes if Processed >= 6, Accuracy >= 67 % and Order >= 60. Soft failure only: at 36 or more souls waiting the supervisor reprimands the player; the shift still ends normally.

Out of scope for the prototype: employee stats, efficiency formula, economy beyond the purse, favour, expansion, night step, Appeals, Detention.

## Dependencies on other roles
| Role | What I need | What I supply |
|---|---|---|
| Game Director | definition of a "sound" verdict; real seconds per case; promotion criteria per rank; whether the clock runs at the desk | counters (Processed, Accuracy, Order, purse), pipeline state, pay formula, per-rank exposure table |
| Narrative | names and personalities for key staff; secret and event text; story surge days; the band-drift schedule; why only about 120 souls a day | event triggers and outcome hooks; meter states that story beats can read or force |
| Art | queue lanes with fixed slot positions; density tiers for overflow; construction and finished states per wing; noticeboard and tally-board props | slot counts per room (Arrival 32 + clump, bench 12), list of visible upgrade changes |
| Technical | fixed-tick sim independent of frame rate; data-driven tuning file; instanced crowds; roster save format; seeded randomness | tier budgets (about 30 embodied NPCs, 12 aggregates, 400 roster rows), tick rates |
| UI/UX | HUD binding for the three stats; desk blotter; shift report; pocket-ledger behaviour; noticeboard read view | exact stat definitions per rank; which data is live and which is "last seen" |
| QA/Producer | a balancing spreadsheet check against these formulas | the worked example as a reference test case |

## Open questions / risks
1. **Walking versus convenience.** Strictly in-world management may be tedious at Rank 4–5 on a phone. Runners, tubes and the bell are my answer; if the UI/UX proposal makes the bottom bar a set of action menus, that contradicts this document and needs a ruling.
2. **Coin meaning changes with rank** (purse, then budget, then treasury). It is consistent as "money you control", but may confuse; the alternative is two separate readouts.
3. **Scale of numbers.** About 120 souls a day is tiny for "every dead human". Either this fortress is one gate of many, or one counted soul stands for a batch. Narrative must choose; the formulas do not care.
4. **Clock at the desk.** I assume time runs during a case. If the Director wants untimed deliberation, the prototype rates must be re-derived from cases per shift instead of seconds.
5. **None of these numbers have been played.** The worked example is arithmetic only. The 2 %/day arrival growth, the Order weights and the morale constants are first guesses and are the most likely to need changing.
6. **Order mixes several causes** (backlog, corruption, guards, incidents). Players may not understand why it moved; each cause needs an in-world tell and a line on the noticeboard.
7. **Sound versus unsound verdicts** sits awkwardly with "no obvious right answer" cases. Ambiguous cases should count every option as sound and carry their consequences through favour and story instead.
