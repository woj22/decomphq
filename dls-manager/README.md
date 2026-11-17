# DLS Manager mod

A football-manager-style game built on top of Dream League Soccer 2019 (v6.15).
The new app provides all menus (club, squad, tactics, fixtures, tables, transfers,
stats, season calendar). DLS19 is used only as the match engine for games you
choose to play; other games can be quick-simulated.

Target content: 2026/27 season, Premier League, LaLiga and the Slovenian PrvaLiga.

**No game files are stored in this repository.** You need your own copy of the
DLS19 APK; the tools here read and patch it locally.

## Layout

```
tools/
  apk_patch/   patch_apk.py   rebuilds the APK with native-code patches + replaced dex
               obb_restore_fix.smali  smali injected into com.savegame.SavesRestoring.DoSmth
  re/          small capstone/pyelftools helpers used to reverse-engineer libDLS19.so
  db/          dls_db.py      reader for the DLS19 database files (assets/data/db/*.dat)
  data/        fetch_transfermarkt.py  pulls squads from the open transfermarkt-datasets export
docs/formats/  file-format notes
```

## Current APK patches (libDLS19.so, arm64)

| Offset | Change | Effect |
|---|---|---|
| 0xf53cc, 0xf7138, 0xf714c | `mov w23,#1` | player-development session limit treated as unlimited |
| 0xba2d8 | `b 0xba30c` | create-player offer always enabled (no tier cap / min games) |
| 0xbab1c–0xbab54 | timer-based type roll + NOPs | create-player card always in the transfer market, random type |
| 0x10ae4c | `mov w9,#0` | development screen stays open after an upgrade |
| 0x10adc8–0x10adcc | `bl 0x10ae34; b 0x10ae08` | skip the development results pop-up |

Java side: `SavesRestoring.DoSmth` re-unpacks the bundled OBB if it is missing or the wrong size.

## Roadmap

1. **Database**: decode players/teams/links, write them back, test a rename in-game. *(players.dat read: done)*
2. **Engine link**: native hook library to start a DLS match with chosen teams and read back result + stats.
3. **Manager shell**: new Android UI as the launch screen, one league, play / quick-sim, stats.
4. **Depth**: three leagues, cups, transfers, contracts, development, season rollover.

## Design decisions

- Menu font: **Manrope** (chosen from Inter, Manrope, Plus Jakarta Sans, DM Sans, Figtree, Outfit).
- Base layout: the dark "Rounded" home-screen concept (top bar, next-match hero, league position card,
  Squad / Tactics / Transfers / Training tiles, latest news strip).

## Data sources

- Squads: [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) open export
  (latest season available: 2025/26; Slovenia not included, so another source is needed).
- Squads (preferred): user-supplied CSVs in `data/user/` (club, player, position, age, nationality,
  contract_expiry, market_value_eur); Wikipedia current squads fill any club not supplied.
- Kits and badges: kit colours/patterns from Wikipedia infoboxes; crests fetched for the local build.

`data/` and `assets/` are git-ignored: this repository is public, so squad data and club
crests stay on the build machine only. Run `tools/data/build_roster.py` to rebuild
`data/roster_2026_27.json` from the sources.
