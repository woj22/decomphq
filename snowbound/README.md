# Snowbound

A sleeper train stopped dead in a mountain blizzard. You are Confucius (compartment 1). Five other passengers -
Napoleon, Florence Nightingale, Nikola Tesla, Cleopatra and Machiavelli - are each played by their own AI calls, and
one of them is a killer. Each night someone may die; each morning the passengers hold a tribunal in the dining car
and vote one person into the freezing baggage car, then vote who sleeps by the stove (warm, watched, an alibi).
Lock up the killer before the snowplough arrives after the third night. If you are locked up yourself, you play on
through the baggage-car door.

**Install (Android, landscape):** copy `apk/snowbound.apk` to the phone and open it. Paste an OpenAI API key on
the start screen (model defaults to `gpt-6-luna`), or play with demo lines.

**Controls:** left thumb joystick to walk, drag anywhere else to look, the gold button to talk / knock / inspect /
sleep. Journal (top right) keeps passengers, trust, clues and notes.

## How it's made
- `tools/build_train.py` + `tools/blib.py`: Blender (bpy) builds the train in modules (compartment, corridor,
  ends and conductor's office, dining bays, bar-and-stove end) and bakes their lighting into lightmaps.
  `tools/make_textures.py` prepares CC0 Poly Haven textures and generates the carpet runner, ceiling and etching.
- `tools/people.py` + `tools/build_people.py`: every character on one shared base made by our own code - body,
  head, hands, skeleton, skin weights and animations (idle, walk, sit, sit_talk, sit_table, talk) - with costumes.
- `scripts/`: `train.gd` (assembly, baked-light materials, blizzard), `person.gd`, `player.gd`, `layout.gd`
  (walkable space, seats, routes), `story.gd` (the truth: culprit, nights, clues, witnesses, votes), `brains.gd`
  (AI prompts: each guest knows only what they could know), `game.gd` (phases, doors, interactions), `ui.gd`.
- Test hooks after `--`: `--autoplay [--demo]` plays a whole game, `--shots=DIR`, `--tour=DIR`; `SB_BASE_URL`
  points the AI client at a mock server.
