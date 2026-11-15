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


def add_maps(bp, rp, world_png, campaign_png, realm_pos):
    """Write wall and table blocks, their textures, the build functions, and return the script that drives them."""
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
                        "minecraft:destructible_by_explosion": False,
                        "minecraft:light_emission": light,
                        "minecraft:map_color": colour,
                    }}}
                p = os.path.join(bp, "blocks", "maps", name + ".json")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                json.dump(block, open(p, "w"), indent=1)

    tiles(world_png, 4, "wall", 4, "#d6c494")
    tiles(campaign_png, 16, "table", 15, "#c8b88a")
    tt = os.path.join(rp, "textures", "terrain_texture.json")
    json.dump({"resource_pack_name": "vaccaria", "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4, "texture_data": terrain},
              open(tt, "w"), indent=1)
    fdir = os.path.join(bp, "functions", NS)
    os.makedirs(fdir, exist_ok=True)
    open(os.path.join(fdir, "mapwall.mcfunction"), "w").write(
        "# Build the 4x4 world map wall three blocks in front of you, facing you\nscriptevent vaccaria:mapwall build\n")
    open(os.path.join(fdir, "campaign_table.mcfunction"), "w").write(
        "# Build the realms campaign table 20 blocks above you (stand somewhere with open sky)\nscriptevent vaccaria:campaign_table build\n")
    realms = [dict(r, u=realm_pos[r["key"]][0], v=realm_pos[r["key"]][1]) for r in REALM_INFO if r["key"] in realm_pos]
    return MAP_SCRIPT.replace("__REALMS__", json.dumps(realms))


MAP_SCRIPT = r'''
// ---- the world map wall and the campaign table ------------------------------------------------------------
import { system as mapSystem, world as mapWorld } from "@minecraft/server";
import { ActionFormData as MapForm } from "@minecraft/server-ui";

const REALMS = __REALMS__;
const busy = new Set();

function facing(p) {
  const k = ((Math.round(p.getRotation().y / 90) % 4) + 4) % 4;      // 0 south, 1 west, 2 north, 3 east
  const f = [[0, 1], [-1, 0], [0, -1], [1, 0]][k];
  return { f, r: [-f[1], f[0]] };                                    // forward, and the viewer's right
}

function buildWall(p) {
  const { f, r } = facing(p);
  const bx = Math.floor(p.location.x) + f[0] * 3, by = Math.floor(p.location.y), bz = Math.floor(p.location.z) + f[1] * 3;
  for (let row = 0; row < 4; row++) for (let col = 0; col < 4; col++) {
    const loc = { x: bx + r[0] * (col - 2), y: by + 4 - row, z: bz + r[1] * (col - 2) };
    p.dimension.getBlock(loc)?.setType(`vaccaria:wall_${row}_${col}`);
  }
  p.sendMessage("§6The map of the world hangs before you. Use it to open the campaign map.");
}

function buildTable(p) {
  const x0 = Math.floor(p.location.x) - 8, z0 = Math.floor(p.location.z) - 8;
  const y = Math.min(Math.floor(p.location.y) + 20, 300);
  for (let r = 0; r < 16; r++) for (let c = 0; c < 16; c++) {
    p.dimension.getBlock({ x: x0 + c, y, z: z0 + r })?.setType(`vaccaria:table_${r}_${c}`);
    for (let k = 1; k <= 14; k++) {
      const b = p.dimension.getBlock({ x: x0 + c, y: y + k, z: z0 + r });
      if (b && !b.isAir) b.setType("minecraft:air");
    }
  }
  mapWorld.setDynamicProperty("vaccaria:table", JSON.stringify({ x: x0, y, z: z0, dim: p.dimension.id }));
  p.sendMessage(`§6The campaign table is ready, 20 blocks above you at ${x0 + 8} ${y} ${z0 + 8}.`);
}

function look(p, t, u, v, height, ease) {
  try {
    p.camera.setCamera("minecraft:free", {
      location: { x: t.x + u * 16, y: t.y + height, z: t.z + v * 16 },
      rotation: { x: 90, y: 180 },
      easeOptions: { easeTime: ease, easeType: "InOutSine" },
    });
  } catch (e) {
    p.runCommand(`camera @s set minecraft:free ease ${ease} in_out_sine pos ${t.x + u * 16} ${t.y + height} ${t.z + v * 16} rot 90 180`);
  }
}

function closeMap(p) {
  try { p.camera.clear(); } catch (e) { p.runCommand("camera @s clear"); }
  busy.delete(p.id);
}

function overview(p, t) {
  look(p, t, 0.5, 0.5, 12.5, 1.2);
  mapSystem.runTimeout(() => {
    const form = new MapForm().title("The Realms of the Empire").body("Choose a realm to study it on the map.");
    for (const r of REALMS) form.button(r.name);
    form.button("§cRoll up the map");
    form.show(p).then((res) => {
      if (res.canceled || res.selection === REALMS.length) return closeMap(p);
      realm(p, t, REALMS[res.selection]);
    });
  }, 30);
}

function realm(p, t, r) {
  look(p, t, r.u, r.v, 5.5, 1.4);
  mapSystem.runTimeout(() => {
    new MapForm().title(r.name)
      .body(`§7Ruler:§r ${r.ruler}\n§7People:§r ${r.people}\n§7Seat:§r ${r.seat}\n\n${r.about}\n\n§6Relations with Vaccaria:§r ${r.relation}`)
      .button("Back to the map").button("§cRoll up the map")
      .show(p).then((res) => {
        if (res.canceled || res.selection === 1) return closeMap(p);
        overview(p, t);
      });
  }, 34);
}

function openCampaign(p) {
  if (busy.has(p.id)) return;
  const raw = mapWorld.getDynamicProperty("vaccaria:table");
  if (!raw) { p.sendMessage("§eBuild the campaign table first: /function vaccaria/campaign_table"); return; }
  busy.add(p.id);
  overview(p, JSON.parse(raw));
}

mapSystem.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity;
  if (!p || p.typeId !== "minecraft:player") return;
  if (ev.id === "vaccaria:mapwall") buildWall(p);
  else if (ev.id === "vaccaria:campaign_table") buildTable(p);
  else if (ev.id === "vaccaria:open_map") openCampaign(p);
});

mapWorld.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (ev.block?.typeId?.startsWith("vaccaria:wall_")) openCampaign(ev.player);
});
'''
