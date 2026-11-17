# DLS19 `players.dat` format

Location in APK: `assets/data/db/players.dat` (also `players_3050.dat`, an older v6 layout).

The file is a single zlib stream (`78 9c`). After inflating:

## Header (12 bytes)

| Offset | Type | Value in v6.15 | Meaning |
|---|---|---|---|
| 0x00 | u32 | 6100 (0x17d4) | magic / DB build id (same value appears in teams.dat, managers.dat, teamplayerlinks_0.dat) |
| 0x04 | u32 | 8 | record layout version (players_3050.dat = 6) |
| 0x08 | u32 | 6121 | record count |

## Record (180 bytes, version 8)

Record size matches the `0xb4` stride used by the game's native code when it walks player arrays.

| Offset | Type | Field | Confidence |
|---|---|---|---|
| 0x00 | u16 | player id | confirmed |
| 0x02 | UTF-16LE[17] | first name | confirmed |
| 0x24 | UTF-16LE[37] | surname | confirmed |
| 0x6E | u16 | nationality id | likely (0–157) |
| 0x70 | u16 | ? (0–8) | unknown, maybe skin tone |
| 0x72 | u16 | ? (1–73) | unknown, maybe head/hair model |
| 0x74 | u16 | ? (0–7) | unknown, maybe hair colour |
| 0x76 | u16 | ? (0–5) | unknown |
| 0x78 | u16 | height (cm) | confirmed (156–204) |
| 0x7A | u16 | weight (kg) | confirmed (60–105) |
| 0x7C–0x82 | u16 ×4 | ? | unknown |
| 0x84 | u16 | ? (0–3, mostly 1) | maybe preferred foot |
| 0x86 | u16[10] | outfield ratings, 0–1000 | confirmed range, order TBD |
| 0x9A | u16[3] | goalkeeper ratings, 0–1000 | confirmed (high only for GKs) |
| 0xA0–0xA6 | u16 ×4 | flags / ? | unknown |
| 0xA8 | u16 | birth day | confirmed |
| 0xAC | u16 | birth month | confirmed |
| 0xB0 | u16 | birth year (1900 = unknown) | confirmed |

Sample (Lukasz Fabianski, GK): outfield `[700,700,625,564,500,500,500,525,525,500]`, GK `[809,686,668]`.

The game's text table lists these ability names, which the 13 ratings probably map to:
speed, acceleration, stamina, control, strength, tackling, passing, shooting, heading, ...,
GK reflexes/diving/positioning. The exact order will be confirmed by comparing in-game screens.

## Still to map

- `teams.dat` (965 KB inflated): team records, including stadium model references (`*.ftm`) and kit data.
- `teamplayerlinks_0.dat` (62 KB): team → player membership (header 6100, 237 teams).
- `managers.dat`: manager names.
