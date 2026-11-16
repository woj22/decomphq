# Alien Worlds for Minecraft Bedrock: villages and farmlands

Three alien villages and two large farmlands, built as Bedrock structures. They come as one behaviour pack, **`AlienWorlds.mcpack`**, which works on mobile.

| Place | Size (x × height × z) | What it is |
|---|---|---|
| **Lumen Hollow** (village) | 96 × 44 × 96 | Nine domed homes (calcite with purple, cyan and magenta bands and coloured glass windows) circle a plaza with a great obsidian ring monument and a floating amethyst core. Giant warped and crimson fungus trees hang shroomlight bulbs, and amethyst crystal spires and glowing pylon-lit paths complete it. Two small farms. |
| **Spireholm** (village) | 96 × 72 × 96 | Six quartz needle towers with purpur and dark-prismarine cone roofs stand on a two-level end-stone terrace. Sky bridges link them, and a 50-block amethyst-tipped great spire rises from a reflecting pool. A crying-obsidian ring gate opens onto a lit quartz avenue. Prismarine crystal spires; beetroot and potato fields. |
| **Hive Ring** (village) | 96 × 40 × 96 | Twelve honeycomb pod houses with copper cone roofs, froglight lamps and lightning-rod antennas, in two rings around a sunken honeycomb-and-copper hive hall under an amber glass crown. Antenna masts; berry, melon and carrot gardens. |
| **Sunwheat Plains** (farmland) | 128 × 36 × 128 | Twelve fully hydrated 25 × 25 fields (wheat, carrots, potatoes, beetroot, melons, pumpkins) on a grid of lit paths with prismarine irrigation pylons. At the centre, a circular pivot field around a water tower carries an **alien crop circle** of short wheat. Also a vaulted glass-roofed hay barn, silos, domed farmhouses, wind spires and a perimeter fence with lanterns. |
| **Terrace Rings** (farmland) | 112 × 48 × 112 | A hill shaped into seven stepped circular terraces of crops, each with its own water channel. Four staircases, diagonal waterfalls, a quartz observatory dome on the summit, irrigation pylons, silos and a barn. |

All the farmland is hydrated: every block is within 4 of water, and the crops are placed fully grown.

Maps are in `maps/`: `<place>_map.png` is a top-down plan with a 16-block chunk grid, and `<place>_preview.png` is an isometric view.

## Import on mobile (Bedrock)
1. Open `AlienWorlds.mcpack` on your phone and Minecraft imports it.
2. Create a world (a **Flat** world is easiest) or edit one: **Behavior Packs → Available → Alien Worlds → Activate**, and turn on **Cheats**. This disables achievements in that world.
3. In the world, stand where you want the **centre** of a place. The ground surface lands at your feet level, and the area is cleared above it.
4. Type `/function alien/lumen_hollow/prepare`. This loads the chunks with a ticking area.
5. Wait about 5 seconds, then type `/function alien/lumen_hollow/build`.
6. When everything has appeared, type `/function alien/lumen_hollow/finish`. This removes the ticking area.

Swap `lumen_hollow` for `spireholm`, `hive_ring`, `sunwheat_plains` or `terrace_rings`. Leave at least 130 blocks between places, or overlap them on purpose.

You can also load single tiles with a structure block or `/structure load alien:<place>_<i>_<j> x y z`. Tiles are 64 × 64; the `build` function lists each tile's offset.

## How it is made
`python3 generator/build_pack.py` regenerates everything in about 2 seconds.
- `generator/layouts.py` holds the places and their parts: domes, needle towers, pod houses, fungus trees, crystal spires, ring monuments, farm plots, barns, silos, pylons and wind spires.
- `generator/vox.py` holds the block palette, shape tools, the `.mcstructure` writer and the map and preview renders.
- `generator/nbt.py` is a little-endian NBT writer.

Blocks are written in the 1.19.0 state format, so the game's block upgrader maps them to current names, for example wool with a `color` state becomes the right coloured wool. Each place is cut into 64 × 64 tiles so `/structure load` handles it on any device.

These files haven't been tested in-game, only generated here. If a block appears as an "update" block or air, tell me which one and I'll fix its name.
