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
