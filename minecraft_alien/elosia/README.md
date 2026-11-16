# Placing the alien city into the Elosia world

These scripts fit the generated villages and farmlands into an existing Bedrock world (Elosia by Zetry), so they sit on its real terrain. The world itself is **not** stored here: its licence asks that it not be re-uploaded.

1. `heightmap.py` reads every chunk's Data3D height map straight from LevelDB, about 15 s for 147k chunks. The top block is the stored value + 63.
2. `sites.py` and `check_sites.py` score land near spawn for flatness, dryness and distance from the centre.
3. `place_city.py` places each layout, using Amulet 1.9 (amulet-leveldb 1.0.2 built with Cython 3.0.11):
   1. finds the real ground under the footprint, ignoring trees and plants;
   2. levels to the median height with cut and fill;
   3. writes the layout in, including its sunken parts;
   4. blends a 14-block skirt back into the hills;
   5. lays lamp-lit deepslate roads that follow the terrain, linking spawn and all five places.
4. `render_area.py` draws a top-down map of the area from the real top blocks.

## Placement

| Place | Centre (x, z) | Ground level |
|---|---|---|
| Lumen Hollow (heart of the city) | (4, -108) | Y 96 |
| Spireholm | (-142, -230) | Y 109 |
| Hive Ring | (282, -218) | Y 110 |
| Sunwheat Plains | (40, -314) | Y 112 |
| Terrace Rings | (-230, -106) | Y 90 |

Spawn is at (0, 0). A road runs north from it into Lumen Hollow.

## Add-on pack (for your own copy of the original Elosia world)
The full edited world is about 620 MB, so `export_pack.py` also produces `Elosia_AlienCity_AddOn.mcpack`, under 1 MB. It cuts each changed region (the five places with their blended terrain, and the five road sections) out of the edited world as 64 × 64 `.mcstructure` tiles at their real coordinates. Block-entity positions such as dungeon chests and spawners are left as structure void, so the player's originals stay intact.

To use it in game:
1. Activate the pack in your Elosia world and turn on cheats.
2. Go to a place (see the table above).
3. Run `/function elosia/<place>/prepare`, wait about 10 seconds, run `/function elosia/<place>/build`, then `/function elosia/<place>/finish`.

The places are `lumen_hollow`, `spireholm`, `hive_ring`, `sunwheat_plains`, `terrace_rings` and `road_1` to `road_5`. Do one at a time: Bedrock allows at most 10 ticking areas.
