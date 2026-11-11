# Last Carriage (Godot 4.6 + Blender)

Midnight. A blizzard has stopped the night train. You and three AIs share a table, each playing a historical
figure; you are the only human. Introductions, then 4 rounds: everyone says who they think the human is and why,
then asks the passenger beside them one yes-or-no question. After round 4, everyone votes. A clear majority
against you means you're unmasked; a tie means you slip away.

**Install on Android:** copy `apk/last-carriage.apk` to the phone and open it (allow "install unknown apps" for
your browser or file manager). Paste your OpenAI API key on the start screen. The model defaults to `gpt-6-luna`
(change it under *Advanced*). *Demo without a key* plays with canned lines.

**Play on desktop:** open this folder in Godot 4.6 and press Play.

## How it's made
- `tools/build_models.py` + `tools/build_passenger.py` (Blender `bpy`, run as plain Python) model the carriage,
  the passengers and the outside, and export `assets/models/*.glb`. The passenger is one rig with every hairstyle,
  beard, hat and costume piece as its own node; `scripts/figures.gd` says which pieces and colours each of the
  21 figures wears.
- `tools/make_textures.py` generates the wood, seat moquette, carpet and paint textures.
- `scripts/`: `world.gd` (carriage, lights, blizzard, look-around camera), `passenger.gd` (dressing, head turns,
  talking), `game.gd` (rules and the three independent AIs), `ai.gd` (OpenAI client), `ui.gd` (HUD), `main.gd`.
- Each AI is a separate Chat Completions call with its own persona, temperament and private notes. The AIs share
  only what is said aloud. The key stays on the device (`user://settings.cfg`, only if *Remember* is ticked).

Rebuild everything: `tools/build_all.sh`. Test hooks (after `--`): `--autoplay` plays one game automatically,
`--demo` uses canned lines, `--shots=DIR` saves a screenshot gallery, `--lineup=DIR` saves close-ups of all figures.
`LC_BASE_URL` points the client at a mock server.
