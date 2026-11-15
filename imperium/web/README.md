# Imperium (browser)

A real-time Three.js vertical slice. You play Cassian Arvel, King of Seravel, on the great terrace of the
Imperial Palace at sunset. Petitioners seek you out, and each decision shifts your Imperial Favour, Treasury,
Influence and Seravel's loyalty. Each decision also moves the evening on, until the capital's windows light up beneath you.

## Run

```
cd imperium/web
python3 -m http.server 8000      # then open http://localhost:8000
```

`?q=0.6` lowers quality (the default on touch devices); `?shot` skips the title screen.

## Controls

WASD / arrows to walk, Shift to stride, drag to look, scroll to zoom, click or tap the floor to walk,
click or tap a petitioner (or press E nearby) to speak, and 1–3 to choose.

## Layout

- `src/city.js` builds the capital from the overhead map (`reference/city_map.png`).
  `tools/map_extract.py` turns the map into `data/citymap.json`, a land-use grid (roofs, streets, water, trees,
  fields, villas) plus street orientation. The capital has instanced buildings, landmarks at their map positions
  (capitol, forum, colosseum, circus, walls and gates, bridges, aqueduct, harbour), and terrain.
- `src/archetypes.js` holds the low-poly building kit.
- `src/palace.js` is the playable terrace (Ionic loggia, statue, braziers, banners).
- `src/figure.js` holds the characters (four species, cloth cloaks, procedural animation). `src/cast.js` has the cast.
- `src/sky.js` is the sunset sky, stars and angular cloud banks.
- `src/story.js` holds the petitions and verdicts.
- `src/main.js` contains the renderer, post-processing, time of day, input, camera, NPCs, dialogue and HUD.
- `vendor/` contains three.js r170 (MIT).
