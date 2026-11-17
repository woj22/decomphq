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
| 0x166ae0 | `b 0x166b10` | badges skip the generated-logo table |
| 0xa75c8, 0xa7638 | `nop`; `b 0xa7660` | imported kits/badges for every team: `DOCS:<id>_home.png` (also `_away`, `_third`, `_home_gk`, `_away_gk`, `_third_gk`) and `DOCS:t<id>.png` / `t<id>_thumb.png`, not just the Dream Team (258) |

| 0x201a58 → 0x525200 | hook + 28-instruction cave (`tools/apk_patch/logo_cave.s`), LOAD[0] grown to 0x525270 | team badges: use `DOCS:teamlogo_<id>.png` / `_thumb.png` when the file exists, instead of the game's 64-entry generated-badge cache |

New players are appended as new `players.dat` records (ids after 16638); overwriting records gave new players the star face keyed to that id (`player/star/h_<id>`, list in `tools/db/star_ids.txt`).

DOCS is `Android/data/com.firsttouchgames.dls3/files`. `assets/dlsmgr_ext.zip` is unpacked there on every launch (kits 512×512 in DLS19 layout, badges 256/64 px). Menu soundtrack: the seven licensed `assets/data/audio/*.m4a` tracks are replaced with 10 s of silence (sound effects in `se.bnk` and Ode to Joy kept).

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

The repository is private. `data/user/` (squad CSVs supplied by the owner) and the
generated `data/roster_2026_27.json` are committed; `assets/` (crests, kit textures) stays
local. Rebuild the roster with:

```
python3 -I tools/data/fetch_wikipedia_squads.py --out <wp_dir>
python3 -I tools/data/build_roster.py --wiki <wp_dir> --tm-players players.csv.gz \
    --user-csv data/user --out data
```

Matching to Transfermarkt uses name + age, so namesakes (e.g. single-name Brazilians)
are not mixed up; unmatched players get placeholder height/foot/date of birth.

## Dream FC = Fužinar (profile)

DLS19 only lets you control your Dream FC, whose squad lives in the save (`profile.dat`), not
in the team database. `tools/save/dls_save.py` reads/writes that file (16-byte header,
XXTEA with the key from `0x7bd234`, Adler-32 seeded `0xabc30526`); round-trips byte for byte.
Any club picked in the menus becomes the Dream FC (`android/src/com/dlsmgr/Profile.java`, on
the device): the menus call `becomeClub(id)`, the app restarts, and before the game reads the save
the squad, development, line-up, set-piece takers, team/short/stadium names are rewritten with the
club's players **by DLS database id** (how the game stores signed players). Custom players stay in
the file (match history refers to them) but leave the squad. Squads come from
`assets/dlsmgr/clubs.json` (`tools/apk_patch/build_club_squads.py`). Backups:
`profile_backup_before_<club>.dat`, `profile_backup_last.dat`; two failed starts after a switch
restore the latter. Writing the players as custom-player records instead (v33,
`tools/save/make_fuzinar_profile.py`) crashed the game, so that path is not used.
The menus' *Export save*
button zips the save so it can be read here; save files are not committed.

## Start-up (first run / after a data reset)

The original mod's `com.savegame.SavesRestoring.DoSmth` (classes2.dex) unpacks the bundled game
data `assets/dl.txt` (the 306 MB OBB) into the OBB folder; nothing is downloaded. Its Turkish
"cheat activated" toasts are replaced with "Setting up DLS Manager…" / "Ready." (string edits in
the apktool tree). The game's Safe Mode is off (`tools/apk_patch/no_safe_mode.smali`).
