# Imperium: the capital for Minecraft Bedrock

`dist/Imperium_Capital.mcworld` is a Bedrock world of the city where the game takes place. It is laid out from the
overhead map (`reference/city_map.png`), with the palace terrace, temples and colosseum styled after the balcony references.

**Install:** open the `.mcworld` file on a device with Minecraft Bedrock, which imports it, or use Play → Worlds → Import.
You spawn on the palace terrace in Creative, at sunset with time frozen, mobs off and coordinates shown.

## What's in it (1.25 blocks per map pixel; the walled city is about 1,750 × 1,050 blocks)
- **Every building is enterable.** About 3,500 houses, insulae and domus have furnished storeys and partitioned rooms,
  each with a hanging lamp, and ladders between floors. Rooms are bedrooms (beds, chests, plants), kitchens (furnace,
  cauldron, food chests), dining rooms and taverns, and shops (grain, wine, smith, cloth, books, pottery) with counters
  and awnings. Some insulae have roof terraces with pergolas. Domus have an atrium with a rain pool and a colonnaded
  garden.
- **The Imperial Palace** stands on the stepped Palatine hill. It has a marble terrace over the city with a crimson
  carpet, statues, braziers, cypress planters and banner poles, plus a grand staircase. The throne hall has a colonnade,
  a dais and a gold throne, and rooms for the council chamber, treasury, library, Hall of Kings and audience room, with
  private quarters upstairs. There are residential wings, a peristyle house and a stair down to the city.
- **The Capitol precinct** has the great temple, with a cult statue, braziers and banners inside, two lesser temples,
  colonnaded stoas with shops and offices, gardens and fountains, a processional way and an altar.
- **The Forum** has the temple of the deified emperor, porticoes of shops, two fountains, statues and market stalls.
- **The Colosseum** has arcaded tiers, a seating rake, corridors underneath, the arena, the emperor's box and awning masts.
- **The Circus** has a track, stands, starting gates, the spina with an obelisk, and turning posts.
- **Other landmarks:** three baths with domed pool halls, rotunda temples, and four more temples.
- **The city's edges:** walls with towers (rooms and ladders inside) and eight gatehouses, lantern-lit avenues to every
  gate, and a road inside the walls. Five bridges cross the river, and the aqueduct carries real water.
- **The harbour** has quays and moored ships with cargo.
- **Countryside:** fields of wheat, carrots and potatoes with irrigation, vineyards, olive groves, meadows, villas and
  roads.

## Regenerate
```
python -m venv venv && . venv/bin/activate
pip install numpy pillow scipy matplotlib "amulet-leveldb==1.0.2"   # leveldb needs Cython 3.0.x to build
python gen_city.py --out ../minecraft_out       # ~1 minute: world folder, .mcworld, map preview
python verify.py ../minecraft_out/world ../minecraft_out
```
- `blocks.py` holds the block palette (Bedrock 1.18 block states, which the game upgrades on load).
- `bedrock.py` writes the chunk records, `level.dat` and `.mcworld`.
- `gen_city.py` is the generator. `preview.py` makes the top-down and isometric renders.
- `verify.py` reads the database back and checks sub-chunks against the source.
