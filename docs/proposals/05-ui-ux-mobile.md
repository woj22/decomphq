# Proposal 05 — UI/UX & Mobile Design: The Purgatory Border

Author: Agent 5 (UI/UX and Mobile). Scope: controls, HUD, dialogue, Judgement Desk, feedback screens, style guide, asset list. Engine standards belong to the Technical Architect; everything here is specified for Godot 4.6 `Control` nodes and one shared `Theme`.

## 1. Principles
1. **World first.** In exploration the HUD covers under 15% of the screen and holds awareness only (where am I, what time, what next). Actions happen at things in the world.
2. **One thumb can play.** Every screen works with a single thumb in landscape; no pinch, no double-tap, no mandatory drag. The only hold gesture is the stamp (and it has a tap alternative).
3. **Paged, never scrolled.** Documents are short cards on pages, so nothing becomes a wall of text and nothing needs a scrollbar.
4. **Heaven is left and gold, Hell is right and red — everywhere.** It matches the concept art, and it gives a spatial and shape cue that does not depend on colour.
5. **Gold and red are not "good" and "bad".** They mean Heaven and Hell only. Selection, flags and warnings use purple and parchment-white, so the UI never tells the player which verdict is right.

## 2. Base resolution and scaling
- **Base UI canvas: 640 x 360 px** (16:9). Stretch aspect `expand`, **integer scale** (2x at 720p, 3x at 1080p, 4x at 1440p), nearest-neighbour filtering. Layouts must tolerate 640-870 px wide (20:9 phones) and 360-512 px high (4:3 tablets) through anchors and containers; extra space goes to the world view and to the document pane, never to bigger chrome.
- On a 6-inch 20:9 phone, **1 base px is about 1.1 dp** (0.17 mm). On a 5.4-inch phone it is about 0.95 dp. All sizes below are base px.
- **Touch targets:** minimum hit area **48 x 48 px** (45-52 dp across phones), primary actions **56-64 px**, at least 8 px between targets. The visible art may be smaller than the hit rectangle (a 24 px icon inside a 48 px button).
- **Safe areas:** the world renders full-bleed. All HUD sits in one root `MarginContainer` whose margins are `max(device safe inset / scale, 12 px)` per side, with bottom at least 16 px for the iOS home indicator. The notch can be on either side in landscape, so both sides are inset independently and re-read on rotation.

## 3. Exploration controls
**Recommended default: tap-to-move, with a floating joystick also active on drag.** If only one can be built for the prototype, build tap-to-move.

| Scheme | Thumb reach | Occlusion | Verdict |
|---|---|---|---|
| Tap-to-move (pathfinding) | Any thumb, one-handed; far targets at top-centre are a stretch | None permanent; finger covers the target briefly | **Default.** Fits isometric doors and "walk to NPC and talk" in one tap |
| Floating joystick (appears where a drag starts) | Thumb rests in the bottom corners, the easiest zone | Thumb and stick cover roughly 15% of a corner while moving | **Secondary, on by default.** Covers far targets and continuous walking |
| Fixed joystick | Poor on varied hand sizes | Permanent | Rejected |

- **Gesture split:** a touch released within 200 ms and 12 px is a tap (walk there; a gold footprint marker shows the destination). A touch that moves further spawns the joystick at the touch point (base 96 px, knob 40 px, 8-direction snapped to the iso axes, dead zone 10 px). Touches that start on a HUD control never move the character.
- **Interacting:** tapping an NPC, door, desk or board walks the character to it and interacts on arrival. With the joystick, the nearest interactable within about 1.5 tiles gets a 1 px gold outline and a floating pip, and the **context action button** (bottom-right, 64 px) shows its verb and icon: Talk, Enter, Sit, Read, Take. No interactable in range hides the button.
- **Entering buildings:** open doors are walk-through triggers with a 0.3 s fade, and a location banner slides in for 2 s. Locked doors show a lock pip and, on tap, a one-line plaque ("Senior Adjudicators only") rather than a popup.
- **Labels:** the mockup's floating location labels appear only on the map view, as the entry banner, and as door plaques when the player is within about 4 tiles. Always-on labels would clutter a 6-inch screen.
- **Left-handed mode** mirrors the HUD horizontally (action button bottom-left, bar bottom-right).

## 4. Exploration HUD
Changes from the concept mockup, with reasons: the bottom-right corner is the best thumb position, so it takes the context action button and the **minimap moves to the top-right** beside a one-line objective strip (tap the strip to expand the full card; tap the minimap for the map). The bottom-left bar shrinks to **Map, Journal, Pause**. Staff, Reports and Upgrades leave the bar and live in the world (section 11).

```
+--------------------------------------------------------------------------+
| [crest] Arrival Hall                    (!) Report to your desk   +-----+ |
|         Day 1 - 09:30                       in Judgement Chambers | map | |
| [soul] 12  [coin] 40  [star] 68%                                  | 72px| |
|                                                                   +-----+ |
|                       .  isometric world, full-bleed  .                   |
|                                  [NPC]                                    |
|                                   (..)  <- interact pip                   |
|                                  [YOU]                                    |
|                                                                           |
| +-----+ +-----+ +-----+                                        +--------+ |
| | Map | |Jrnl | |Pause|                                        |  TALK  | |
| +-----+ +-----+ +-----+                                        +--------+ |
+--------------------------------------------------------------------------+
```
- Top-left panel: 168 x 56 px. Three stats with 16 px icons, bound to whatever the Director defines (proposed for the prototype: souls waiting, wages, standing). Tapping a stat shows a one-line tooltip for 2 s.
- Bar buttons: 48 x 48 px, 24 px icon over a 12 px caption. Journal holds the objective list, case notes and a dialogue log.
- Notifications arrive as a messenger note sliding from the top-left panel, never as a modal. The HUD hides during dialogue, the desk and ceremonies.

## 5. Dialogue UI
```
+--------------------------------------------------------------------------+
|                    world dimmed 40%, camera eases to the speaker          |
|                                                                           |
|                                       +---------------------------------+ |
|                                       | 1  "I was told to report here." | |
|                                       | 2  "What happens to the souls?" | |
|                                       | 3  (Say nothing)                | |
|                                       +---------------------------------+ |
| +--------+ +-[ SUPERVISOR MORWEN ]-----------------------------[Log]---+ |
| |portrait| | You are late, clerk. The dead are not. Sit down, read the  | |
| | 64x64  | | file, and do not stamp anything until I say so.         v  | |
| +--------+ +----------------------------------------------------------- + |
+--------------------------------------------------------------------------+
```
- Panel 104 px high, anchored bottom and full width inside the safe area. Portrait 64 x 64 in a gold frame; the player's own lines put the portrait on the right. Name plate is a tab on the panel's top edge.
- **Text reveal:** typewriter at 40 characters per second (settings: slow, normal, instant) with a soft quill tick every third character. First tap completes the line, second tap advances. A bobbing arrow marks "more".
- **Length rule for writers:** at most 3 lines and about 140 characters per box; longer speech is split into boxes.
- **Choices:** up to 4, stacked above the panel on the thumb side, each a full-width button at least 48 px high, numbered. Choices that need a rank, flag or item show a small icon and the reason when unavailable; they are never hidden silently.
- Tapping anywhere on the panel advances. Log reopens the last 20 lines.

## 6. Soul Judgement Desk
The desk is entered by sitting at the player's desk in the Judgement Chambers (camera pushes in for 0.25 s). It is a full-screen scene, not an overlay.

### 6.1 Recommendation
- **Prototype: tabbed folder.** One document pane with vertical index tabs. It is buildable from `PanelContainer`, `VBoxContainer` and buttons, needs no drag physics, and is fully usable with one thumb.
- **Later ("Desk 2.0"): draggable documents.** Papers physically slide out of the booth slot onto a desk surface, can be laid two-up for comparison, and the stamp is dragged from a rack. This is the richer, more tactile version, but it needs drag, z-ordering, snap zones and careful small-screen tuning. An intermediate step is a "pin beside" action that shows two tabs side by side on wide phones.

### 6.2 Prototype layout
```
+--------------------------------------------------------------------------+
| [< Leave desk]   Case 3 of 8      Shift 11:40      Waiting: 5             |
| +-----------+ +----+--------------------------------------+ +----------+ |
| |  booth    | |FILE| LIFE RECORD                    p 1/2 | |   ASK    | |
| |  window   | +----+--------------------------------------+ |  about   | |
| |  soul     | |REC*| 1881  Born in Lowmoor, a miller's son | +----------+ |
| |  bust     | +----+--------------------------------------+ |   FLAG   | |
| |  96x96    | |ARCH|>1903  Deserted his regiment at Varn < | |    0/6   | |
| |           | +----+--------------------------------------+ +----------+ |
| | Tobias    | |TALK| 1904  Hid two families from soldiers  |              |
| | Ferrow    | +----+--------------------------------------+ +----------+ |
| | "I did    | |NOTE| 1931  Died owing a debt to his brother| |  PASS    | |
| | what I    | +----+--------------------------------------+ | JUDGEMENT| |
| | could."   |      |        [< page]        [page >]       | +----------+ |
| +-----------+      +--------------------------------------+              |
+--------------------------------------------------------------------------+
```
Columns at 640 px: booth 132, tabs 48, document pane 316 (this column grows on wider phones), actions 96, with 8 px gaps and 12 px margins.

- **Booth (left).** The soul's bust, name and current spoken line in a speech bubble. Mood is shown by a 3-frame expression change, not a meter.
- **Tabs.** FILE (one-page summary: name, dates, cause of death, the soul's own claim), RECORD (life entries), ARCHIVE (documents requested from Records), TALK (questions), NOTES (flagged entries). A dot on a tab means unread content.
- **Entries, not paragraphs.** Each fact is one card: a year or source, then at most 2 lines and about 80 characters. Maximum 5 cards per page and 3 pages per tab, with page-turn buttons and a paper-flip sound. Each card is 48 px tall and tappable.
- **Select, then act.** Tapping a card lifts it by 2 px with a purple edge. The action column then applies to it:
  - **ASK** makes the soul respond to that entry. The answer appears in the booth bubble and is added to TALK as a new card, which can itself be flagged.
  - **FLAG** pins the card with a purple ribbon and copies it to NOTES (limit 6). When two flagged cards form a contradiction, NOTES joins them with a red thread labelled "Discrepancy" and a new confrontation question unlocks in TALK. Flagging is free and reversible.
- **Archive cross-reference.** The ARCHIVE tab lists 2-3 requestable files per case ("Parish register", "Court ledger"). A request sends a capsule up a pneumatic tube, costs shift time, and returns one page of cards. Later ranks may require walking to the Records Department or sending a runner, which ties the desk back to exploration.
- **TALK.** Up to 4 general questions as 48 px buttons; asked questions grey out and their answers stay as cards.
- **PASS JUDGEMENT** (96 x 64, always visible) opens the verdict view. It is never disabled; judging without investigating is the player's right and has consequences.

### 6.3 Verdict and stamp confirmation
```
+--------------------------------------------------------------------------+
| [< Back to file]              FINAL JUDGEMENT                             |
|                                                                           |
|  +-----------+      +----------------------------+      +-----------+    |
|  |  (halo)   |      |  Tobias Ferrow, 1881-1931  |      |  (flame)  |    |
|  |  HEAVEN   |      |  Flags: 2   Discrepancy: 1 |      |   HELL    |    |
|  |   stamp   |      |  Archive consulted: 1 of 2 |      |   stamp   |    |
|  +-----------+      |                            |      +-----------+    |
|   gold door         |    [ imprint lands here ]  |        red door        |
|                     +----------------------------+                        |
|              Choose a stamp, then hold it on the writ to seal             |
+--------------------------------------------------------------------------+
```
- Step 1: tap HEAVEN (left, halo icon, gold) or HELL (right, flame icon, red). The chosen stamp lifts and hovers over the writ; the other dims. Tapping the other stamp switches; Back returns to the file with nothing lost.
- Step 2: **hold on the writ for 0.6 s.** A ring fills, then the stamp slams down. Settings offer "tap to confirm" instead of hold. This two-step flow prevents accidental irreversible verdicts.
- **Feedback (about 1.2 s, then control returns):** a heavy thunk, 2 px screen shake, a 40 ms haptic pulse, an ink imprint rotated by a random few degrees, and the writ whisked into the tube. The booth shows the soul leaving through the left door into rising gold motes, or the right door into a red glow. Shake and haptics can be switched off.
- **No "correct/incorrect" flash.** Procedural errors (a missed discrepancy) arrive as a citation slip from the supervisor before the next case. Moral consequences surface later in the shift report and in the world. This needs the Director's agreement.

## 7. End-of-shift report
Shown when the player leaves the desk at shift end (or is told the bell has rung). A parchment ledger over the darkened desk.
```
+--------------------------------------------------------------------------+
|        +----------------------------------------------------------+      |
|        |  SHIFT LEDGER - Day 1          Junior Processing Clerk   |      |
|        |----------------------------------------------------------|      |
|        |  Souls processed        8      (halo) 5     (flame) 3    |      |
|        |  Discrepancies found    4 of 6                           |      |
|        |  Citations              1      "Case 5: record ignored"  |      |
|        |  Wages  +40    Deductions  -5    Balance  75             |      |
|        |  Standing  [#########.......]  62%   next rank at 80%    |      |
|        |----------------------------------------------------------|      |
|        |  Note: "The Ferrow family has lodged an appeal."         |      |
|        |                                   [ Sign and leave ]     |      |
|        +----------------------------------------------------------+      |
+--------------------------------------------------------------------------+
```
Rows write in one at a time (0.25 s each, tap to skip). At most 6 rows and one narrative note. The single button is the player signing the ledger; the game saves here.

## 8. Promotion ceremony
Triggered in the world: the supervisor summons the player and the ceremony plays in that room. The screen is the closing beat.
```
+--------------------------------------------------------------------------+
|                         By order of the Chancery                          |
|                                                                           |
|            Junior Processing Clerk   --->   SENIOR ADJUDICATOR            |
|                               +------------+                              |
|                               |  new seal  |                              |
|                               |   96x96    |                              |
|                               +------------+                              |
|     [key]  Records Department opened to you                               |
|     [quill] Appeals may now be heard at your desk                         |
|     [coin] Wages raised to 60 per shift                                   |
|                          [ Accept the seal ]                              |
+--------------------------------------------------------------------------+
```
The seal presses into wax with the same thunk as the stamp. At most 3 privileges, each with an icon. After acceptance the HUD crest changes and a newly unlocked door is shown by a short camera pan.

## 9. Pause and settings
Pause (bar button, or automatically when the app loses focus) opens a charcoal panel: Resume, Journal, Settings, Save and quit to title. Settings use 48 px rows with large toggles and stepped sliders, grouped as **Controls** (tap-to-move, joystick, left-handed mirror, hold or tap to stamp), **Reading** (text size Standard/Large, text speed, fully opaque panels), **Feel** (haptics, screen shake, flashes), **Sound** (music, effects, voice blips) and **Vision** (Heaven/Hell pattern overlays, on by default).

## 10. Onboarding
Taught in the world by the player's supervisor on Day 1. No tutorial screens and no text popups.
1. **Move:** the supervisor says "Follow me" and walks ahead; a gold footprint marks where to tap.
2. **Interact:** she stops at the desk and waits; the context button pulses.
3. **Cases 1-3:** she stands at the booth. Case 1 (obvious) teaches FILE, RECORD and the stamp; Case 2 adds FLAG and a discrepancy; Case 3 adds the archive tube. From Case 4 she leaves.

Overlay budget: one pulsing gold ring around a single control at a time, nothing modal, the game never pauses for a hint, and a hint repeats after 8 s of inactivity. A dialogue choice ("I have done this before") skips the guided cases on later playthroughs.

## 11. Keeping later systems in the world
Rule: **every full-screen interface has a physical origin** (a desk, board, ledger or person), opens with a camera push-in toward it, and closes with a "step back" button in the same top-left position as "Leave desk". There is no global management menu.

| Function (mockup button) | Opened at | From rank |
|---|---|---|
| Soul judgement | The player's desk | 1 |
| Map | Minimap, wall maps in halls | 1 |
| Staff | Duty roster board in Administrative Offices; talking to the employee | 3 |
| Reports | Ledger on the player's own desk; the auditor NPC | 2-3 |
| Upgrades | Works Office clerk at a requisitions counter | 3 |
| Budgets | Treasury ledger | 4 |
| Diplomacy | Envoys in the Diplomatic Quarter; a negotiating-table screen | 4 |

Alerts reach the player as messengers and notes that say where to go. Remote convenience is earned, not given: at high rank a speaking tube in the player's office can summon people to it. All these screens reuse the desk's components (tabs, cards, paged parchment, stamp-style confirmation).

## 12. Style guide
| Token | Hex | Use |
|---|---|---|
| Charcoal panel | `#1B1A20` at 92% | HUD and dialogue panels |
| Panel edge | `#3A3742` | Inner 1 px line, dividers |
| Border gold | `#C9A24B` | 1 px panel borders with notched corners |
| Text light | `#EDE6D6` | Text on charcoal |
| Text dim | `#A59E90` | Captions, disabled |
| Parchment | `#E6D9B8` / shade `#CBB98F` | Documents, ledgers |
| Ink | `#2A2320` | Text on parchment |
| Heaven gold | `#F2C75C` | Heaven stamp, halo, left door only |
| Hell red | `#B3261E` / ember `#E2553A` | Hell stamp, flame, right door only |
| Muted purple | `#7A63A0` | Selection, flags, focus |

- Panels are 9-patch (`StyleBoxTexture`, 24 x 24 source, 8 px margins). Documents never use charcoal and chrome never uses parchment, so the eye separates "tool" from "evidence" at once.
- Text contrast is at least 7:1 (light on charcoal, ink on parchment). Red and gold are used as fills and icons with a text label, never as body text colour.
- Motion is short and physical: 0.15-0.3 s slides, paper flips, stamp slams. No bounces or glows on chrome.

### Fonts (all freely licensed; licence files bundled beside the fonts)
| Role | Font | Licence | Size |
|---|---|---|---|
| Display: stamps, rank titles, building names | **Jacquard 24** (pixel blackletter) | SIL OFL | 24 and 48 px, at most 3 words |
| Body, dialogue, cards, buttons | **Pixel Operator** / Pixel Operator Bold | CC0 | 16 px |
| Case numbers, dates, ledgers (optional) | **Departure Mono** | SIL OFL | 11 or 22 px |
| Large-text mode body | **Jersey 20** | SIL OFL | 20 px |
| Alternates | Pixelify Sans (OFL), monogram (CC0) | | |

Fallback if nothing can be bundled: Godot's built-in default font at 16 px with antialiasing off. Layouts are sized for 16 px body text so the fallback fits.

### Pixel-font readability rules
- Use each font only at its native size or an integer multiple (native sizes to be confirmed on import). No fractional scaling, antialiasing, faux bold or italics.
- Essential text is never below 16 px (about 2.8 mm on a 6-inch phone). Captions are 12 px minimum and never carry meaning alone.
- Blackletter is for short titles only; body text is mixed case. Line height 1.25x; about 45 characters per line in documents and 70 in dialogue.
- Every text container is paged or auto-wrapping so Large mode (+25%) and localisation do not break layouts.

### Colour-blind and one-handed
- Heaven/Hell are always distinguished by position (left/right), icon (halo/flame), word and an optional hatch pattern as well as colour. Flags use a ribbon shape plus purple; discrepancies use a drawn thread plus a label.
- All primary actions sit within reach of one thumb at a bottom corner or the right edge; mirrored in left-handed mode. No simultaneous two-finger input anywhere.

## 13. Prototype UI asset list (base px, procedurally generated)
| Asset | Size | Count |
|---|---|---|
| Panel 9-patches: charcoal, parchment, button (normal/pressed/disabled), tab (on/off), card (normal/selected/flagged) | 24 x 24 each | 10 |
| HUD crest (rank 1, rank 2) | 32 x 32 | 2 |
| Stat icons: soul, coin, standing | 16 x 16 | 3 |
| Bar icons: map, journal, pause, settings | 24 x 24 | 4 |
| Context action icons: talk, enter, sit, read, take, locked | 24 x 24 | 6 |
| Context action button frame | 64 x 64 | 1 |
| Joystick base / knob | 96 x 96 / 40 x 40 | 2 |
| Tap destination marker (4 frames) | 16 x 8 | 1 |
| Interact pip, objective marker, unread dot, "more" arrow | 16 x 16 | 4 |
| Minimap frame and player/objective blips | 72 x 72, 4 x 4 | 3 |
| Dialogue portrait frame; NPC portraits | 64 x 64 | 1 + per NPC |
| Soul busts for the booth (3 expressions) | 96 x 96 | per soul |
| Booth window frame, left gold door, right red door | 132 x 200 | 3 |
| Desk tab icons: file, record, archive, talk, notes | 24 x 24 | 5 |
| Action icons: ask, flag ribbon, judge gavel, page left/right, tube capsule | 24 x 24 | 6 |
| Stamps (halo, flame) and ink imprints | 64 x 64, 96 x 48 | 4 |
| Hold-to-stamp ring (8 frames) | 48 x 48 | 1 |
| Parchment tile, red discrepancy thread, wax seal | 64 x 64, 8 x 8, 96 x 96 | 3 |
| Promotion privilege icons: key, quill, coin | 24 x 24 | 3 |
| Sounds (with Audio owner): tap, page flip, quill tick, tube whoosh, stamp thunk, bell | | 6 |

## 14. Dependencies on other roles
- **Technical Architect:** confirm 640 x 360 base, integer scaling, `expand` aspect and nearest filtering; safe-area insets exposed to the HUD root; pathfinding on the iso grid for tap-to-move; touch input routing (HUD consumes touches before the world); one shared `Theme`; haptics; save at shift sign-off.
- **Game Director:** the three HUD stats; shift clock and time cost of archive requests; whether verdict feedback is delayed as proposed; the flag/discrepancy rule and flag limit; what "standing" is and promotion thresholds.
- **Narrative:** writing limits (140 characters per dialogue box, 80 per record card, 5 cards per page, 3 pages per tab, 4 choices); the supervisor's name and Day 1 script; contradiction pairs tagged in case data.
- **Art:** palette agreement with the hex tokens above; portrait (64) and bust (96) sizes; world tile scale so the 1.5-tile interaction radius and labels read correctly; all assets in section 13 generated by script.
- **Management/Sim:** each management function mapped to a physical object and reusing card/tab/ledger components; no data view that needs more than about 5 rows per page.
- **QA/Producer:** device matrix (5.4-inch 16:9 to 6.8-inch 20:9, one 4:3 tablet), notch on both sides, one-handed playthrough test, Large-text pass.

## 15. Open questions / risks
1. **Departure from the mockup HUD:** minimap moved to top-right and Staff/Reports/Upgrades removed from the bar. This follows the "not a menu game" brief but needs owner sign-off.
2. **640 x 360 may conflict with the art pipeline's chosen world resolution.** If the world uses a different base, the UI can sit on its own canvas layer at 640 x 360, but integer scaling must hold for both.
3. **Font availability and native sizes are unverified in this environment.** If the fonts cannot be downloaded, the fallback is Godot's default font and the blackletter display style is lost until a font is generated or bundled.
4. **Tap versus drag disambiguation** (200 ms / 12 px) needs tuning on real devices; a wrong threshold makes movement feel unresponsive.
5. **Document pane width (316 px on 16:9)** limits cards to about 42 characters per line. If cases need more text, the booth column must collapse to a strip while reading.
6. **Delayed verdict feedback** may feel unrewarding in a short prototype; the citation slip and shift report carry all the reinforcement.
7. **Hold-to-stamp** is tactile but is a known accessibility barrier; the tap alternative must ship in the prototype, not later.
8. **Software-rendered screenshots** cannot verify touch feel, haptics or safe areas; those need a physical device before the control scheme is locked.
