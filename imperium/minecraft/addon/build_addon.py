"""Build the Vaccaria Council add-on (behaviour pack + resource pack) as a .mcaddon.

  python build_addon.py SKIN.png [--out DIR]

SKIN.png is the cow skin (64x64). The script paints a rank sash onto it in 12 colours, writes both packs, and zips them.
The Principality of Vaccaria: 12 ranks of cow-folk NPCs who walk, open doors, look at you and each other, talk
(a dialogue window when you interact), and either flee danger or (guard ranks) fight hostile mobs. Ranks 1-3 are
reserved for five named councillors who sit with you on the Emperor's council.
"""
import argparse
import json
import os
import shutil
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
NS = "vaccaria"
ENTITY = NS + ":cow_folk"
BP_UUID, BP_DATA, BP_SCRIPT = "a7986c19-ab18-4eb7-b874-55b91b19a090", "f69b767d-d95f-4566-8649-ba4bc105351c", "f2150648-13c5-45b0-8766-bfea44bed88a"
RP_UUID, RP_RES = "8fbdd496-9ef3-459c-84a4-4b18f4142a53", "69027871-2e46-44f8-97fd-d9c685aba689"
VERSION = [1, 3, 0]

# rank, title, sash colour, guard?, weight when spawned at random (0 = reserved for named characters)
RANKS = [
    (1, "Lord Chancellor of Vaccaria", (232, 184, 48), False, 0),
    (2, "High Steward", (106, 44, 154), False, 0),
    (3, "Envoy to the Imperial Council", (160, 30, 42), False, 0),
    (4, "Magistrate", (42, 63, 154), False, 4),
    (5, "Knight-Warden", (200, 204, 212), True, 4),
    (6, "Captain of the Herd Guard", (47, 107, 52), True, 4),
    (7, "Archivist", (31, 138, 138), False, 6),
    (8, "Guildmaster", (217, 121, 42), False, 6),
    (9, "Sergeant of the Guard", (34, 34, 38), True, 10),
    (10, "Herald", (194, 64, 138), False, 8),
    (11, "Yeoman", (125, 186, 58), False, 16),
    (12, "Herdhand", (230, 230, 230), False, 22),
]
COUNCIL = [
    (1, "Lord Chancellor Bram Hornwick"),
    (2, "High Steward Odalie Clovermere"),
    (2, "High Steward Tamsin Brindle"),
    (3, "Envoy Fennick Moorlow"),
    (3, "Envoy Hesper Dunhorn"),
]


# ------------------------------------------------------------------------------------------------ textures
def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c) + (255,)


def sash(base, rank, colour):
    """Paint a 2-pixel diagonal sash from the right shoulder to the left hip, front and back, over the torso.
    The top three ranks get gold edging and a medallion where the sash crosses the chest."""
    img = base.copy()
    px = img.load()
    main, dark = shade(colour, 1.0), shade(colour, 0.72)
    gold, gold_d = (240, 196, 70, 255), (190, 140, 40, 255)
    top = rank <= 3

    def band(x0, y0, w, h, mirror):
        for y in range(h):
            c = (w - 1) - (y * (w - 1) / (h - 1)) if not mirror else (y * (w - 1) / (h - 1))
            for x in range(w):
                d = x - c
                if -1.0 <= d < 1.0:
                    px[x0 + x, y0 + y] = main
                elif -2.0 <= d < -1.0 or 1.0 <= d < 2.0:
                    px[x0 + x, y0 + y] = (gold if top else dark) if (d < -1.0) == (not mirror) else (gold_d if top else dark)

    band(20, 20, 8, 12, False)          # chest
    band(32, 20, 8, 12, True)           # back
    # over the right shoulder (top of the body) and around the left hip (left side face)
    for x in range(20, 22):
        for y in range(16, 20):
            px[x, y] = main
    for y in range(28, 32):
        for x in range(28, 32):
            px[x, y] = main if y < 30 else dark
    for y in range(20, 23):
        for x in range(16, 20):
            px[x, y] = main
    if top:
        # medallion on the chest, and a gold fringe at the hip knot
        cx, cy = 24, 25
        for (dx, dy) in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
            px[cx + dx, cy + dy] = gold
        px[cx, cy] = (255, 236, 150, 255)
        for x in (28, 30):
            px[x, 31] = gold
    return img


def textures(skin_path, out_dir):
    base = Image.open(skin_path).convert("RGBA")
    if base.size != (64, 64):
        raise SystemExit("the skin must be a 64x64 PNG (got %s)" % (base.size,))
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for rank, title, colour, guard, w in RANKS:
        p = os.path.join(out_dir, "rank_%02d.png" % rank)
        sash(base, rank, colour).save(p)
        paths.append(p)
    return paths


# ------------------------------------------------------------------------------------------------ packs
def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, indent=2)


def behaviour_pack(d):
    write(os.path.join(d, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "Vaccaria Council (behaviour)", "description": "The cow-folk of the Principality of Vaccaria: 12 ranks of humanlike NPCs.",
                   "uuid": BP_UUID, "version": VERSION, "min_engine_version": [1, 21, 50]},
        "modules": [{"type": "data", "uuid": BP_DATA, "version": VERSION},
                    {"type": "script", "language": "javascript", "uuid": BP_SCRIPT, "entry": "scripts/main.js", "version": VERSION}],
        "dependencies": [{"uuid": RP_UUID, "version": VERSION}, {"module_name": "@minecraft/server", "version": "1.16.0"},
                         {"module_name": "@minecraft/server-ui", "version": "1.3.0"}],
    })
    groups = {}
    for rank, title, colour, guard, w in RANKS:
        groups["%s:rank_%d" % (NS, rank)] = {"minecraft:variant": {"value": rank}}
    groups[NS + ":guard"] = {
        "minecraft:equipment": {"table": "loot_tables/vaccaria/guard_gear.json"},
        "minecraft:attack": {"damage": 5},
        "minecraft:behavior.melee_attack": {"priority": 2, "speed_multiplier": 1.15, "track_target": True},
        "minecraft:behavior.hurt_by_target": {"priority": 1},
        "minecraft:behavior.nearest_attackable_target": {"priority": 3, "must_see": True, "reselect_targets": True, "within_radius": 16,
                                                         "entity_types": [{"filters": {"all_of": [{"test": "is_family", "subject": "other", "value": "monster"},
                                                                                                  {"test": "is_family", "subject": "other", "operator": "!=", "value": "creeper"}]},
                                                                           "max_dist": 16}]},
    }
    groups[NS + ":civilian"] = {
        "minecraft:behavior.panic": {"priority": 1, "speed_multiplier": 1.3},
        "minecraft:behavior.avoid_mob_type": {"priority": 2, "entity_types": [{"filters": {"test": "is_family", "subject": "other", "value": "monster"},
                                                                                "max_dist": 10, "walk_speed_multiplier": 0.8, "sprint_speed_multiplier": 1.1}]},
    }
    groups[NS + ":council"] = {
        "minecraft:nameable": {"always_show": True, "allow_name_tag_renaming": False},
        "minecraft:home": {"restriction_radius": 12},
        "minecraft:behavior.random_stroll": {"priority": 8, "speed_multiplier": 0.5, "xz_dist": 4},
    }
    events = {}
    rnd = []
    for rank, title, colour, guard, w in RANKS:
        role = NS + (":guard" if guard else ":civilian")
        events["%s:make_rank_%d" % (NS, rank)] = {"add": {"component_groups": ["%s:rank_%d" % (NS, rank), role] + ([NS + ":council"] if rank <= 3 else [])}}
        if w:
            rnd.append({"weight": w, "add": {"component_groups": ["%s:rank_%d" % (NS, rank), role]}})
    events["minecraft:entity_spawned"] = {"randomize": rnd}
    events[NS + ":make_random"] = {"randomize": rnd}
    events[NS + ":greeted"] = {}
    entity = {
        "format_version": "1.20.80",
        "minecraft:entity": {
            "description": {"identifier": ENTITY, "is_spawnable": True, "is_summonable": True, "is_experimental": False},
            "component_groups": groups,
            "components": {
                "minecraft:type_family": {"family": ["vaccaria", "cow_folk", "npc", "mob"]},
                "minecraft:collision_box": {"width": 0.6, "height": 1.9},
                "minecraft:health": {"value": 24, "max": 24},
                "minecraft:physics": {}, "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
                "minecraft:persistent": {},
                "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": True},
                "minecraft:movement": {"value": 0.5},
                "minecraft:navigation.walk": {"can_path_over_water": False, "avoid_water": True, "can_open_doors": True, "can_pass_doors": True,
                                              "avoid_damage_blocks": True, "can_walk_in_lava": False},
                "minecraft:movement.basic": {}, "minecraft:jump.static": {}, "minecraft:can_climb": {},
                "minecraft:annotation.open_door": {},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.open_door": {"priority": 5, "close_door_after": True},
                "minecraft:behavior.random_stroll": {"priority": 8, "speed_multiplier": 0.6, "xz_dist": 10},
                "minecraft:behavior.look_at_player": {"priority": 6, "look_distance": 8, "probability": 0.04},
                "minecraft:behavior.look_at_entity": {"priority": 7, "look_distance": 6, "probability": 0.03,
                                                      "filters": {"test": "is_family", "subject": "other", "value": "vaccaria"}},
                "minecraft:behavior.random_look_around": {"priority": 9},
                "minecraft:interact": {"interactions": [{"on_interact": {"filters": {"test": "is_family", "subject": "other", "value": "player"},
                                                                         "event": NS + ":greeted", "target": "self"},
                                                         "interact_text": "action.interact.talk"}]},
                "minecraft:conditional_bandwidth_optimization": {},
            },
            "events": events,
        },
    }
    write(os.path.join(d, "entities", "cow_folk.json"), entity)
    write(os.path.join(d, "loot_tables", "vaccaria", "guard_gear.json"),
          {"pools": [{"rolls": 1, "entries": [{"type": "item", "name": "minecraft:iron_sword", "weight": 1}]}]})
    # summoning helpers
    council = ["# The Vaccaria delegation to the Emperor's council: five named councillors around you"]
    offs = [(0, 3), (-3, 2), (3, 2), (-2, 4), (2, 4)]
    for (rank, name), (dx, dz) in zip(COUNCIL, offs):
        council.append('summon %s ~%d ~ ~%d %s:make_rank_%d "%s"' % (ENTITY, dx, dz, NS, rank, name))
    write(os.path.join(d, "functions", "vaccaria", "council.mcfunction"), "\n".join(council) + "\n")
    folk = ["# A dozen Vaccaria cow-folk of random ranks (4-12) around you"]
    for k in range(12):
        folk.append("summon %s ~%d ~ ~%d %s:make_random" % (ENTITY, (k % 4) * 2 - 3, (k // 4) * 2 + 2, NS))
    write(os.path.join(d, "functions", "vaccaria", "folk.mcfunction"), "\n".join(folk) + "\n")
    for rank, title, colour, guard, w in RANKS:
        write(os.path.join(d, "functions", "vaccaria", "rank_%d.mcfunction" % rank), "summon %s ~ ~ ~2 %s:make_rank_%d\n" % (ENTITY, NS, rank))
    # dialogue script
    ranks_js = json.dumps({r: t for r, t, *_ in RANKS})
    council_js = json.dumps({n: r for r, n in COUNCIL})
    script = r'''// Vaccaria cow-folk: talk to any of them. The named councillors have their own lines.
import { world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

const RANKS = __RANKS__;
const COUNCIL = __COUNCIL__;
const GIVEN = ["Alda", "Bertram", "Clover", "Dunstan", "Elsbeth", "Fenwick", "Gilda", "Hamlin", "Isolde", "Jory", "Kestrel", "Linden", "Marlow", "Nell", "Osric", "Primrose", "Quill", "Rowan", "Sorrel", "Tobin", "Una", "Varo", "Wynn", "Yarrow"];
const FAMILY = ["Hornwick", "Clovermere", "Brindle", "Moorlow", "Dunhorn", "Meadowby", "Fallowfield", "Oxley", "Barleycombe", "Stillwater", "Hayward", "Thistledown"];

const LINES = {
  council: {
    "Lord Chancellor Bram Hornwick": [
      "Highness. When the Emperor's council sits, Vaccaria will speak with one voice: yours. I will see to it the others remember that.",
      "The other kingdoms count their legions. We count our friends. Ours is the longer list, if we are careful.",
    ],
    "High Steward Odalie Clovermere": [
      "The treasury ledgers are in order, Highness. If the Imperial assessors ask for more, I will show them exactly what we have, and not a coin more.",
      "Vaccaria's granaries could feed half the province. That is a fact the Emperor's council will want to hear, and pay for.",
    ],
    "High Steward Tamsin Brindle": [
      "I have the guest lists for the council feast. Seat the southern kings far from the northern ones, and the night may end without a duel.",
      "Your quarters in the palace are ready, Highness. I had the cushions aired twice.",
    ],
    "Envoy Fennick Moorlow": [
      "I have spoken to the envoys of three kingdoms this week. Two want our support. One wants our pastures. I told none of them anything.",
      "At the council, watch the Chancellor of the Treasury's hands. He taps the table before he lies.",
    ],
    "Envoy Hesper Dunhorn": [
      "The Emperor's herald has confirmed our seats, Highness: second row, left of the throne. Closer than last year.",
      "If the council calls a vote on the frontier levies, let me speak first. I know what the Legions will accept.",
    ],
  },
  rank: {
    4: ["Justice in Vaccaria is swift and fair, Highness. Mostly swift."],
    5: ["The roads are safe while the Knight-Wardens ride them."],
    6: ["The Herd Guard stands ready, Highness. Say the word."],
    7: ["Every treaty Vaccaria ever signed is in my archive. Some of them twice."],
    8: ["Trade is good this season. The guilds send their respects, and their invoices."],
    9: ["Keep close to the guard, Highness. These streets are busy tonight."],
    10: ["Hear ye! Make way for the Prince!"],
    11: ["A fine day for it, Highness."],
    12: ["Highness! Oh, I didn't see you there."],
  },
};

const pick = (a, seed) => a[Math.abs(seed) % a.length];
function hash(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return h; }

function identity(entity) {
  const rank = entity.getComponent("minecraft:variant")?.value ?? 12;
  let name = entity.nameTag;
  if (!name) {
    // ordinary cow-folk get a stable name from their id the first time you speak to them
    const h = hash(entity.id);
    name = `${pick(GIVEN, h)} ${pick(FAMILY, h >> 5)}`;
    try { entity.nameTag = name; } catch (e) { /* ignore */ }
  }
  return { rank, name, title: RANKS[rank] };
}

function talk(player, entity) {
  const who = identity(entity);
  const own = COUNCIL[who.name] !== undefined ? LINES.council[who.name] : null;
  const opening = own ? own[0] : pick(LINES.rank[who.rank] ?? LINES.rank[12], hash(entity.id));
  const form = new ActionFormData()
    .title(who.name)
    .body(`§7${who.title} of Vaccaria§r\n\n${opening}`)
    .button("Tell me about Vaccaria")
    .button("What news of the Emperor's council?")
    .button("Carry on");
  form.show(player).then((r) => {
    if (r.canceled || r.selection === 2) return;
    const reply = r.selection === 0
      ? "Vaccaria: green hills, deep wells and the stubbornest cattle in the Empire. We are a small principality, Highness, but we are a loyal one, and the Emperor knows it."
      : (own ? own[1] : "The council sits soon, Highness. The Lord Chancellor and the envoys will stand beside you. The rest of us will keep the principality running while you are gone.");
    new ActionFormData().title(who.name).body(reply).button("Thank you").show(player);
  });
}

world.afterEvents.playerInteractWithEntity.subscribe((ev) => {
  if (ev.target?.typeId === "__ENTITY__") talk(ev.player, ev.target);
});
'''.replace("__RANKS__", ranks_js).replace("__COUNCIL__", council_js).replace("__ENTITY__", ENTITY)
    write(os.path.join(d, "scripts", "main.js"), script)
    write(os.path.join(d, "texts", "en_US.lang"), "pack.name=Vaccaria Council\n")


GEOMETRY = {
    "format_version": "1.12.0",
    "minecraft:geometry": [{
        "description": {"identifier": "geometry.vaccaria.cow_folk", "texture_width": 64, "texture_height": 64,
                        "visible_bounds_width": 2, "visible_bounds_height": 3, "visible_bounds_offset": [0, 1.5, 0]},
        "bones": [
            {"name": "root", "pivot": [0, 0, 0]},
            {"name": "waist", "parent": "root", "pivot": [0, 12, 0]},
            {"name": "body", "parent": "waist", "pivot": [0, 24, 0], "cubes": [{"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 16]}]},
            {"name": "jacket", "parent": "body", "pivot": [0, 24, 0], "cubes": [{"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 32], "inflate": 0.25}]},
            {"name": "head", "parent": "body", "pivot": [0, 24, 0], "cubes": [{"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [0, 0]}]},
            {"name": "hat", "parent": "head", "pivot": [0, 24, 0], "cubes": [{"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [32, 0], "inflate": 0.5}]},
            {"name": "rightArm", "parent": "body", "pivot": [-5, 22, 0], "cubes": [{"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 16]}]},
            {"name": "rightSleeve", "parent": "rightArm", "pivot": [-5, 22, 0], "cubes": [{"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 32], "inflate": 0.25}]},
            {"name": "rightItem", "parent": "rightArm", "pivot": [-6, 15, 1]},
            {"name": "leftArm", "parent": "body", "pivot": [5, 22, 0], "cubes": [{"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [32, 48]}]},
            {"name": "leftSleeve", "parent": "leftArm", "pivot": [5, 22, 0], "cubes": [{"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [48, 48], "inflate": 0.25}]},
            {"name": "leftItem", "parent": "leftArm", "pivot": [6, 15, 1]},
            {"name": "rightLeg", "parent": "root", "pivot": [-1.9, 12, 0], "cubes": [{"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}]},
            {"name": "rightPants", "parent": "rightLeg", "pivot": [-1.9, 12, 0], "cubes": [{"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 32], "inflate": 0.25}]},
            {"name": "leftLeg", "parent": "root", "pivot": [1.9, 12, 0], "cubes": [{"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [16, 48]}]},
            {"name": "leftPants", "parent": "leftLeg", "pivot": [1.9, 12, 0], "cubes": [{"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [0, 48], "inflate": 0.25}]},
        ],
    }],
}


def resource_pack(d, tex_paths):
    write(os.path.join(d, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "Vaccaria Council (resources)", "description": "Skins and model for the cow-folk of Vaccaria.",
                   "uuid": RP_UUID, "version": VERSION, "min_engine_version": [1, 21, 50]},
        "modules": [{"type": "resources", "uuid": RP_RES, "version": VERSION}],
        "dependencies": [{"uuid": BP_UUID, "version": VERSION}],
    })
    tdir = os.path.join(d, "textures", "entity", "vaccaria")
    os.makedirs(tdir, exist_ok=True)
    for p in tex_paths:
        shutil.copy(p, os.path.join(tdir, os.path.basename(p)))
    textures = {"rank_%d" % r: "textures/entity/vaccaria/rank_%02d" % r for r, *_ in RANKS}
    write(os.path.join(d, "entity", "cow_folk.entity.json"), {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": ENTITY,
            "materials": {"default": "entity_alphatest"},
            "textures": textures,
            "geometry": {"default": "geometry.vaccaria.cow_folk"},
            "scripts": {"initialize": ["variable.gliding_speed_value = 1.0;"],
                        "pre_animation": ["variable.tcos0 = (math.cos(query.modified_distance_moved * 38.17) * query.modified_move_speed / variable.gliding_speed_value) * 57.3;"],
                        "animate": ["humanoid_base_pose", "look_at_target_default", "move", "bob", "holding"]},
            "animations": {"humanoid_base_pose": "animation.humanoid.base_pose", "look_at_target_default": "animation.humanoid.look_at_target.default",
                           "move": "animation.humanoid.move", "bob": "animation.humanoid.bob", "holding": "animation.humanoid.holding"},
            "render_controllers": ["controller.render.vaccaria.cow_folk"],
            "enable_attachables": True,
            "spawn_egg": {"base_color": "#4a3324", "overlay_color": "#d8a23a"},
        }},
    })
    write(os.path.join(d, "models", "entity", "cow_folk.geo.json"), GEOMETRY)
    write(os.path.join(d, "render_controllers", "cow_folk.render_controllers.json"), {
        "format_version": "1.8.0",
        "render_controllers": {"controller.render.vaccaria.cow_folk": {
            "arrays": {"textures": {"Array.skins": ["Texture.rank_%d" % r for r, *_ in RANKS]}},
            "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[math.clamp(query.variant - 1, 0, 11)]"]}},
    })
    write(os.path.join(d, "texts", "en_US.lang"),
          "entity.%s.name=Vaccaria Cow-Folk\nitem.spawn_egg.entity.%s.name=Spawn Vaccaria Cow-Folk\npack.name=Vaccaria Council\n" % (ENTITY, ENTITY))
    write(os.path.join(d, "texts", "languages.json"), ["en_US"])


def zipdir(src, zf, prefix):
    for root, _, files in os.walk(src):
        for f in files:
            p = os.path.join(root, f)
            zf.write(p, os.path.join(prefix, os.path.relpath(p, src)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skin")
    ap.add_argument("--out", default=os.path.join(HERE, "build"))
    ap.add_argument("--world-map", help="world map image (512x512) for the 4x4 map wall")
    ap.add_argument("--campaign", help="campaign map image (1024x1024) for the 16x16 campaign table")
    ap.add_argument("--realm-pos", help="JSON of realm name -> [u, v] centre on the campaign map")
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    tex = textures(a.skin, os.path.join(a.out, "textures"))
    bp, rp = os.path.join(a.out, "Vaccaria_BP"), os.path.join(a.out, "Vaccaria_RP")
    behaviour_pack(bp)
    resource_pack(rp, tex)
    if a.world_map and a.campaign and a.realm_pos:
        import maps_addon
        extra = maps_addon.add_maps(bp, rp, a.world_map, a.campaign, json.load(open(a.realm_pos)))
        with open(os.path.join(bp, "scripts", "main.js"), "a") as f:
            f.write(extra)
    out = os.path.join(a.out, "Vaccaria_Council.mcaddon")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        zipdir(bp, z, "Vaccaria_BP")
        zipdir(rp, z, "Vaccaria_RP")
    print("wrote", out)


if __name__ == "__main__":
    main()
