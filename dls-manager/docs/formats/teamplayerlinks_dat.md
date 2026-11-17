# DLS19 `teamplayerlinks_0.dat` format

Location: `assets/data/db/teamplayerlinks_0.dat`, a single zlib stream.

## Header (16 bytes)

| Offset | Type | Value | Meaning |
|---|---|---|---|
| 0x00 | u32 | 6100 | DB build id (same as players.dat) |
| 0x04 | u32 | 237 | team-id table size (one more than the 236 blocks present) |
| 0x08 | u32 | 0xFFFFFFFF | ? |
| 0x0C | u32 | 0 | ? |

## Team block (264 bytes) × 236

| Offset | Type | Field |
|---|---|---|
| 0x00 | u32 | team id (0–573, matches teams.dat) |
| 0x04 | u32 | number of players `n` (16–31 in v6.15) |
| 0x08 | 32 × {u8 shirt, u8 position slot, u8 flags, u8 0} | per-player squad info, first `n` used |
| 0x88 | 32 × u32 | player ids (players.dat `id`), first `n` used, rest 0xFFFFFFFF |

Example, team 0 = Arsenal (2018): `(10, 18, 0x39)` Özil, `(14, 19, 5)` Aubameyang,
`(1, 0, 1)` Leno, `(6, 5, 3)` Koscielny.

### Flags byte (bit meanings inferred from the Arsenal and Aston Villa squads)

| Bit | Meaning |
|---|---|
| 0x01 | in the starting XI |
| 0x02 | captain |
| 0x04 | penalty taker |
| 0x08 | free-kick taker |
| 0x10 | left corner taker |
| 0x20 | right corner taker |

### Position slot codes (observed counts across all squads)

0 = GK, 1 = LB, 2 = RB, 5 / 7 = CB, 8–13 = defensive/central midfield variants,
16 = RM, 17 = LM, 18 = AM, 19 = ST, 20–22 = wide forwards. Exact names still to confirm
against the in-game formation screen.

Validation: all 4,804 links point at existing players; 415 players appear in more than one
team (club + national team).
