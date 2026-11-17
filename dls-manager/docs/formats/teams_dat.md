# DLS19 `teams.dat` format (partial)

Location: `assets/data/db/teams.dat`, a single zlib stream.

## Header (12 bytes)

| Offset | Type | Value | Meaning |
|---|---|---|---|
| 0x00 | u32 | 6100 | DB build id |
| 0x04 | u32 | 9 | record layout version |
| 0x08 | u32 | 236 | team count |

## Team record (4,092 bytes) × 236

| Offset | Type | Field | Confidence |
|---|---|---|---|
| 0x000 | u32 | team id (matches teamplayerlinks_0.dat) | confirmed |
| 0x004 | u32 | ? (0/1) | unknown, maybe club vs national team |
| 0x008 | u32 | ? (0x10, 2, 0xFFFFFFFF) | unknown |
| 0x00C | 4 × u8 | ? (`51 51 50 00` for Arsenal) | unknown, maybe kit pattern ids |
| 0x010–0x10B | RGBA × ~63 | kit colours (home / away / third / GK; shirt, sleeves, shorts, socks, trims) | likely; `0xFFFFFFFF` = unused slot |
| 0x10C | 8 × u8 | ? (`03 09 09 04 04 04 04 00`) | likely kit pattern/style indices |
| 0x114 | u32 × 5 | player ids: captain, free-kick, left corner, penalty, right corner | confirmed for Arsenal (Koscielny, Özil, Özil, Aubameyang, Özil) |
| 0x128 | bytes | `00 00 47 00 42 00 00 00 05 02 14 00 …` | unknown, likely formation / tactics / rating |
| 0x140 | UTF-16LE | stadium name (`Arsenal Stadium`) | confirmed |
| 0x170–0x54B | ASCII[52] × ~19 | stadium prop models (`camera1.ftm`, `microphone.ftm`, …) | confirmed |
| 0xE74–0xFBE | ASCII[32] × ~10 | stand models (`corner_g_3_a.ftm`, `side_g_3_a.ftm`, …) and seat texture | confirmed |

Team **names are not in this file**: they live in `assets/data/text/ftsteamnames.xlc`
(FTTL text bank, keys `TXT_TEAMNAMELONG_<team id>` and short variants, 14 languages).
That format still needs decoding before names can be rewritten.
