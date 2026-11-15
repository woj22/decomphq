"""Map wall and campaign table for the Vaccaria add-on.

- The world map wall: 4x4 blocks (128 px each) showing the whole world as a vanilla map would draw it at the
  most zoomed-out scale (one map pixel per chunk), with unexplored paper around the edge.
- The campaign table: 16x16 glowing blocks (64 px each) showing the realms map. Clicking the wall lifts the camera
  over the table; pick a realm and the camera glides down to it with a panel about that realm.
Both are built in-game by script (/function vaccaria/mapwall, /function vaccaria/campaign_table).
"""
import json
import os

from PIL import Image

NS = "vaccaria"

REALM_INFO = [
    {"key": "The Imperial Heartland", "name": "The Imperial Heartland", "ruler": "His Imperial Majesty Aurex IV Valerran",
     "people": "Humans, the Imperial Kin", "seat": "The Imperial Council, in the caldera of the volcano",
     "about": "The Emperor's own lands around the great volcano, where the Imperial Council sits and every king comes to bow.",
     "relation": "Your liege. The Throne expects tribute, levies and loyalty, in that order."},
    {"key": "Velithra", "name": "Velithra", "ruler": "Queen Ilsaveth Anorai", "people": "Veyari",
     "seat": "The blossom courts of the north", "about": "Scholars, diplomats and merchants of the cherry-blossom north.",
     "relation": "Cordial. Velithra trades with everyone and trusts no one."},
    {"key": "Karst Odun", "name": "Karst Odun", "ruler": "King Oduvar Brunnhak", "people": "Othari",
     "seat": "The halls under the frozen peaks", "about": "Miners and smiths of the frozen western mountains.",
     "relation": "Neutral. They sell steel to whoever pays."},
    {"key": "Khar-Dumeth", "name": "Khar-Dumeth", "ruler": "King Thrask Ur-Vashen", "people": "Kharad",
     "seat": "The river fortresses", "about": "A warrior kingdom holding the rich river lands at the heart of the continent.",
     "relation": "Wary. Thrask wants the client kings to stand together against the Imperial assessors."},
    {"key": "Tor-Ilun", "name": "Tor-Ilun", "ruler": "Queen Vashka Tor-Ilun", "people": "Kharad",
     "seat": "The red mesas", "about": "Badlands and deserts of the south-east, rich in copper and stubborn pride.",
     "relation": "Distant. Few in Vaccaria have met a Tor-Ilun envoy."},
    {"key": "Lucerna", "name": "Lucerna", "ruler": "King Marcellan Dorr", "people": "Humans",
     "seat": "The lowland capital", "about": "Rich lowlands and mesas, and Vaccaria's great neighbour to the east.",
     "relation": "Your neighbour. Friendly for now, but Lucernan nobles eye your pastures."},
    {"key": "Meridia", "name": "Meridia", "ruler": "Governor Halvana Pryce", "people": "An Imperial province",
     "seat": "The governor's palace on the southern isles", "about": "Southern isles governed directly from the capital.",
     "relation": "Imperial officials: correct, and watchful."},
    {"key": "Principality of Vaccaria", "name": "The Principality of Vaccaria", "ruler": "The Prince of Vaccaria (you)", "people": "Cow-folk",
     "seat": "Your hall", "about": "A small principality of green hills and deep wells. Small, for now.",
     "relation": "Home."},
]

PAPER = (214, 196, 148)


def world_map_image(samples_pkl, out_png, chunks_lo=-192, size=512, margin=64):
    """Vanilla-style map from per-chunk samples: (cx, cz, map colour name, mean height, water depth)."""
    import pickle
    import numpy as np
    from vmap_colours import MC
    data = pickle.load(open(samples_pkl, 'rb'))
    n = size - 2 * margin
    kind = {}
    h = np.full((n, n), np.nan)
    depth = np.zeros((n, n))
    for cx, cz, c, hh, dd in data:
        x, z = cx - chunks_lo, cz - chunks_lo
        if 0 <= x < n and 0 <= z < n:
            kind[(x, z)] = c
            h[z, x] = hh
            depth[z, x] = dd
    img = np.zeros((size, size, 3), np.uint8)
    img[:] = PAPER
    sh = (180 / 255, 220 / 255, 1.0)
    for (x, z), c in kind.items():
        base = MC.get(c) or MC['STONE']
        if c == 'WATER':
            d = depth[z, x] * 0.1 + ((x + z) & 1) * 0.2
            k = 2 if d < 0.5 else 0 if d > 0.9 else 1
        else:
            hn = h[z - 1, x] if z > 0 and not np.isnan(h[z - 1, x]) else h[z, x]
            d = (h[z, x] - hn) * 0.5 + (((x + z) & 1) - 0.5) * 0.4
            k = 2 if d > 0.6 else 0 if d < -0.6 else 1
        img[z + margin, x + margin] = [int(v * sh[k]) for v in base]
    # a thin darker paper edge, like the rim of a map item
    img[:4, :] = img[-4:, :] = img[:, :4] = img[:, -4:] = (150, 128, 88)
    Image.fromarray(img).save(out_png)
    return out_png


def map_icon(path):
    """A folded parchment map with a red route and a gold compass point (original 16x16 pixel art)."""
    from PIL import ImageDraw
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(1, 3), (5, 1), (10, 3), (15, 1), (15, 13), (10, 15), (5, 13), (1, 15)], fill=(224, 206, 160, 255))
    d.line([(5, 1), (5, 13)], fill=(190, 168, 120, 255)); d.line([(10, 3), (10, 15)], fill=(190, 168, 120, 255))
    d.polygon([(2, 6), (4, 5), (4, 9), (2, 10)], fill=(120, 160, 90, 255)); d.polygon([(11, 6), (14, 5), (14, 10), (11, 11)], fill=(150, 160, 190, 255))
    d.line([(3, 12), (7, 9), (9, 10), (13, 6)], fill=(170, 40, 40, 255))
    d.point((12, 3), fill=(230, 180, 60, 255)); d.point((7, 6), fill=(230, 180, 60, 255))
    d.line([(1, 3), (1, 15)], fill=(140, 110, 70, 255))
    im.save(path)


def add_maps(bp, rp, world_png, campaign_png, realm_pos):
    """The campaign map as an on-screen menu: a picture of the realms at the top of the form, buttons for each realm.
    The old wall and table blocks stay defined (so any already placed can still be seen and cleared)."""
    terrain = {}
    tex_dir = os.path.join(rp, "textures", "blocks", NS)
    os.makedirs(tex_dir, exist_ok=True)

    def tiles(img_path, n, prefix, light, colour):
        im = Image.open(img_path).convert("RGB")
        tile = im.width // n
        for r in range(n):
            for c in range(n):
                name = "%s_%d_%d" % (prefix, r, c)
                im.crop((c * tile, r * tile, c * tile + tile, r * tile + tile)).save(os.path.join(tex_dir, name + ".png"))
                terrain["%s_%s" % (NS, name)] = {"textures": "textures/blocks/%s/%s" % (NS, name)}
                block = {"format_version": "1.21.40", "minecraft:block": {
                    "description": {"identifier": "%s:%s" % (NS, name), "menu_category": {"category": "none"}},
                    "components": {
                        "minecraft:material_instances": {"*": {"texture": "%s_%s" % (NS, name), "render_method": "opaque"}},
                        "minecraft:destructible_by_mining": {"seconds_to_destroy": 0.3},
                        "minecraft:light_emission": light,
                    }}}
                p = os.path.join(bp, "blocks", "maps", name + ".json")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                json.dump(block, open(p, "w"), indent=1)

    tiles(world_png, 4, "wall", 4, "#d6c494")
    tiles(campaign_png, 16, "table", 15, "#c8b88a")
    json.dump({"resource_pack_name": "vaccaria", "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4, "texture_data": terrain},
              open(os.path.join(rp, "textures", "terrain_texture.json"), "w"), indent=1)

    # pictures for the menu: the whole map, and a close-up of each realm
    ui_dir = os.path.join(rp, "textures", "ui", NS)
    os.makedirs(ui_dir, exist_ok=True)
    full = Image.open(campaign_png).convert("RGB")
    full.resize((512, 512), Image.LANCZOS).save(os.path.join(ui_dir, "map_overview.png"))
    realms = []
    for i, r in enumerate(REALM_INFO):
        if r["key"] not in realm_pos:
            continue
        u, v = realm_pos[r["key"]]
        half = int(full.width * 0.2)
        cx, cy = int(u * full.width), int(v * full.height)
        cx, cy = min(max(cx, half), full.width - half), min(max(cy, half), full.height - half)
        full.crop((cx - half, cy - half, cx + half, cy + half)).resize((512, 512), Image.LANCZOS).save(os.path.join(ui_dir, "map_realm_%d.png" % i))
        realms.append(dict(r, tex="textures/ui/%s/map_realm_%d" % (NS, i)))
    OVERVIEW = "The Realms of the Empire"
    pics = [(OVERVIEW, "textures/ui/%s/map_overview" % NS)] + [(r["name"], r["tex"]) for r in realms]
    controls = []
    for k, (title, tex) in enumerate(pics):
        controls.append({"vaccaria_map_%d" % k: {
            "type": "image", "texture": tex, "size": ["100%", "100%x"],
            "bindings": [{"binding_name": "#title_text"},
                         {"binding_type": "view", "source_property_name": "(#title_text = '%s')" % title, "target_property_name": "#visible"}]}})
    ui = {"namespace": "server_form",
          "long_form_scrolling_content": {"modifications": [{"array_name": "controls", "operation": "insert_front", "value": controls}]}}
    os.makedirs(os.path.join(rp, "ui"), exist_ok=True)
    json.dump(ui, open(os.path.join(rp, "ui", "server_form.json"), "w"), indent=1)

    # the Map Lectern: a placeable stand with the map on its slanted top; using it opens the campaign map
    W = 128
    tex = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    import random as _r
    rnd = _r.Random(3)
    wood = Image.new("RGB", (64, 64))
    for y in range(64):                                   # oak planks: bands with grain and dark seams
        for x in range(64):
            band = (y // 8) % 2
            base = (156, 120, 72) if band else (146, 110, 64)
            g = rnd.randint(-10, 10) + (8 if (x + y * 3) % 17 == 0 else 0)
            c = tuple(max(0, min(255, v + g)) for v in base)
            if y % 8 == 0 or (x + (y // 8) * 23) % 32 == 0:
                c = (98, 72, 40)
            wood.putpixel((x, y), c)
    tex.paste(wood, (0, 0))
    mp = full.resize((60, 60), Image.LANCZOS)
    edge = Image.new("RGB", (64, 64), (92, 64, 36))
    edge.paste(mp, (2, 2))
    tex.paste(edge, (64, 0))
    tex.save(os.path.join(tex_dir, "map_lectern.png"))
    terrain[NS + "_map_lectern"] = {"textures": "textures/blocks/%s/map_lectern" % NS}

    def faces(w, h, d, top=None):
        f = {k: {"uv": [0, 0], "uv_size": [s1, s2]} for k, (s1, s2) in
             {"north": (w, h), "south": (w, h), "east": (d, h), "west": (d, h), "up": (w, d), "down": (w, d)}.items()}
        if top:
            f["up"] = {"uv": [64, 0], "uv_size": [64, 64]}
        return f
    geo = {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": "geometry.vaccaria.map_lectern", "texture_width": W, "texture_height": W},
        "bones": [{"name": "lectern", "pivot": [0, 0, 0], "cubes": [
            {"origin": [-6, 0, -6], "size": [12, 2, 12], "uv": faces(12, 2, 12)},
            {"origin": [-2, 2, -2], "size": [4, 10, 4], "uv": faces(4, 10, 4)},
            {"origin": [-7, 12, -6], "size": [14, 2, 12], "pivot": [0, 13, 0], "rotation": [-22.5, 0, 0], "uv": faces(14, 2, 12, top=True)},
            {"origin": [-7, 11.5, -7], "size": [14, 1, 1], "pivot": [0, 13, 0], "rotation": [-22.5, 0, 0], "uv": faces(14, 1, 1)},
        ]}]}]}
    os.makedirs(os.path.join(rp, "models", "blocks"), exist_ok=True)
    json.dump(geo, open(os.path.join(rp, "models", "blocks", "map_lectern.geo.json"), "w"), indent=1)
    rot = {"north": 0, "west": 90, "south": 180, "east": -90}
    block = {"format_version": "1.21.40", "minecraft:block": {
        "description": {"identifier": NS + ":map_lectern", "menu_category": {"category": "items"},
                        "traits": {"minecraft:placement_direction": {"enabled_states": ["minecraft:cardinal_direction"], "y_rotation_offset": 180}}},
        "components": {
            "minecraft:geometry": "geometry.vaccaria.map_lectern",
            "minecraft:material_instances": {"*": {"texture": NS + "_map_lectern", "render_method": "alpha_test"}},
            "minecraft:collision_box": {"origin": [-7, 0, -7], "size": [14, 15, 14]},
            "minecraft:selection_box": {"origin": [-7, 0, -7], "size": [14, 16, 14]},
            "minecraft:destructible_by_mining": {"seconds_to_destroy": 1.0},
            "minecraft:light_dampening": 0,
            "minecraft:custom_components": [NS + ":open_map"],
        },
        "permutations": [{"condition": "q.block_state('minecraft:cardinal_direction') == '%s'" % k,
                          "components": {"minecraft:transformation": {"rotation": [0, v, 0]}}} for k, v in rot.items()]}}
    json.dump(block, open(os.path.join(bp, "blocks", "map_lectern.json"), "w"), indent=1)
    json.dump({"resource_pack_name": "vaccaria", "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4, "texture_data": terrain},
              open(os.path.join(rp, "textures", "terrain_texture.json"), "w"), indent=1)
    with open(os.path.join(rp, "texts", "en_US.lang"), "a") as f:
        f.write("tile.%s:map_lectern.name=Map Lectern\n" % NS)

    fdir = os.path.join(bp, "functions", NS)
    os.makedirs(fdir, exist_ok=True)
    open(os.path.join(fdir, "map.mcfunction"), "w").write("# Open the campaign map\nscriptevent vaccaria:open_map menu\n")
    open(os.path.join(fdir, "map_lectern.mcfunction"), "w").write("# Get a Map Lectern: place it, then use it to open the campaign map\ngive @s vaccaria:map_lectern\n")
    open(os.path.join(fdir, "clear_maps.mcfunction"), "w").write(
        "# Remove any old map walls and campaign tables (and stray map blocks within 32 blocks of you)\nscriptevent vaccaria:clear_maps all\n")
    return MAP_SCRIPT.replace("__REALMS__", json.dumps(realms)).replace("__OVERVIEW__", OVERVIEW)


MAP_SCRIPT = r"""
// ---- the campaign map: an on-screen menu ------------------------------------------------------------------
import { system as mapSystem, world as mapWorld } from "@minecraft/server";
import { ActionFormData as MapForm } from "@minecraft/server-ui";

const REALMS = __REALMS__;

function overview(p) {
  const form = new MapForm().title("__OVERVIEW__").body("Choose a realm to study it.");
  for (const r of REALMS) form.button(r.name);
  form.button("§cRoll up the map");
  form.show(p).then((res) => {
    if (res.canceled || res.selection === REALMS.length) return;
    realm(p, REALMS[res.selection]);
  });
}

function realm(p, r) {
  new MapForm().title(r.name)
    .body(`§7Ruler:§r ${r.ruler}\n§7People:§r ${r.people}\n§7Seat:§r ${r.seat}\n\n${r.about}\n\n§6Relations with Vaccaria:§r ${r.relation}`)
    .button("Back to the map").button("§cRoll up the map")
    .show(p).then((res) => {
      if (res.canceled || res.selection === 1) return;
      overview(p);
    });
}

// clearing any map walls or tables built by earlier versions
let removed = 0;
const isMapBlock = (id) => id?.startsWith("vaccaria:wall_") || id?.startsWith("vaccaria:table_");
function clearMaps(p) {
  removed = 0;
  const wipe = (dim, loc) => { const b = dim.getBlock(loc); if (b && isMapBlock(b.typeId)) { b.setType("minecraft:air"); removed++; } };
  let list = [];
  try { list = JSON.parse(mapWorld.getDynamicProperty("vaccaria:builds") ?? "[]"); } catch (e) { }
  const t = mapWorld.getDynamicProperty("vaccaria:table");
  if (t) { const o = JSON.parse(t); list.push({ kind: "table", dim: o.dim, x: o.x, y: o.y, z: o.z }); }
  for (const b of list) {
    let dim;
    try { dim = mapWorld.getDimension(b.dim); } catch (e) { continue; }
    try {
      if (b.kind === "table") { for (let r = 0; r < 16; r++) for (let c = 0; c < 16; c++) wipe(dim, { x: b.x + c, y: b.y, z: b.z + r }); }
      else for (const l of b.blocks) wipe(dim, l);
    } catch (e) { }
  }
  mapWorld.setDynamicProperty("vaccaria:builds", undefined);
  mapWorld.setDynamicProperty("vaccaria:table", undefined);
  const dim = p.dimension, cx = Math.floor(p.location.x), cy = Math.floor(p.location.y), cz = Math.floor(p.location.z);
  const R = 32, Y0 = -24, Y1 = 48;
  let x = -R;
  notify(p, "§6Clearing old map blocks...");
  const id = mapSystem.runInterval(() => {
    for (let k = 0; k < 2 && x <= R; k++, x++) {
      for (let z = -R; z <= R; z++) for (let y = Y0; y <= Y1; y++) {
        try { wipe(dim, { x: cx + x, y: cy + y, z: cz + z }); } catch (e) { }
      }
    }
    if (x > R) { mapSystem.clearRun(id); notify(p, `§6Removed ${removed} old map blocks.`); }
    else if (x % 16 === 0) notify(p, `§6Clearing... ${Math.round((x + R) / (2 * R) * 100)}%`);
  }, 1);
}

mapSystem.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity;
  if (!p || p.typeId !== "minecraft:player") return;
  if (ev.id === "vaccaria:open_map") overview(p);
  else if (ev.id === "vaccaria:clear_maps") clearMaps(p);
});

const lastOpen = new Map();
function openFromLectern(p) {
  if (!p || mapSystem.currentTick - (lastOpen.get(p.id) ?? -99) < 10) return;
  lastOpen.set(p.id, mapSystem.currentTick);
  overview(p);
}
try {
  mapWorld.beforeEvents.worldInitialize.subscribe((ev) => {
    ev.blockComponentRegistry.registerCustomComponent("vaccaria:open_map", { onPlayerInteract: (e) => openFromLectern(e.player) });
  });
} catch (e) { }
mapWorld.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (ev.block?.typeId === "vaccaria:map_lectern") openFromLectern(ev.player);
});
"""
