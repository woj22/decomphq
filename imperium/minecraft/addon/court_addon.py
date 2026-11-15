"""The Imperial court: 16 named characters as summonable NPCs (vaccaria:courtier).

They share the cow-folk's behaviour (talking, following, the Steward's Ledger, sleeping at night). Each has a skin
chosen from a skin pack the user owns (given as a folder + cast_skins.json mapping), converted from the legacy 64x32
layout to 64x64 the same way Minecraft does, and their own lines of dialogue.
"""
import json
import os

from PIL import Image, ImageOps

NS = "vaccaria"
ENTITY = NS + ":courtier"

# name tag, full name, title, realm, guard?, dialogue (opening, council news)
CHARS = [
    ("Aurex", "Aurex IV Valerran", "Emperor", "the Empire", False,
     ["Little Vaccaria's prince. Your tribute arrives on time, and your cattle feed my legions. I notice such things.",
      "The council will hear every king and decide nothing until I speak. Learn to wait well, prince. It is most of ruling."]),
    ("Sabine", "Sabine Valerran", "Empress", "the Empire", False,
     ["You have your mother's manners, prince. Keep them; they are rarer at this court than gold.",
      "The kings will quarrel over the levies. Sit near me at the feast and you will hear who is bluffing."]),
    ("Valen", "Valen Valerran", "Crown Prince", "the Empire", False,
     ["Another prince! Thank the gods. Everyone else here is a hundred years old or a lizard.",
      "Father says I must attend every session this year. If you see me asleep, kick my chair."]),
    ("Decimar", "Decimar Thane", "Marshal of the Legions", "the Empire", True,
     ["The Legions remember who sends cohorts and who sends excuses, Highness.",
      "The Khar border is quiet. Too quiet. I will ask the council for more auxiliaries, and I will get them."]),
    ("Cassia", "Cassia Varro", "Praetorian Prefect", "the Empire", True,
     ["Keep your hands where my guards can see them, Highness. It is nothing personal.",
      "Every envoy who enters the caldera is searched twice. The council chamber is the safest room in the Empire. I make sure of it."]),
    ("Severa", "Severa Ostian", "Prefect of the Palace", "the Empire", False,
     ["Your quarters, your audience times and your seat at council all pass through my office, Highness. Be courteous to my clerks.",
      "The agenda is set. Tribute first, then the levies, then whatever Thrask shouts about."]),
    ("Nyssal", "Nyssal Vey-Tamir", "Count of the Treasury", "the Empire", False,
     ["Ah, the cattle prince. Your ledgers are tidy. Suspiciously tidy.",
      "The Treasury proposes a modest increase in tribute. Modest for whom is a matter for debate."]),
    ("Sethiel", "Sethiel Aurn", "Imperial Herald", "the Empire", False,
     ["Prince of Vaccaria! Your name is on my list. Near the bottom, but on it.",
      "When the council opens I announce every ruler in order of precedence. Do try to look impressive when I reach you."]),
    ("Korrach", "Korrach Venn", "Legate of the Auxilia", "the Empire", True,
     ["Your herd guards march well, little prince. For grass-eaters.",
      "The auxilia want pay, not speeches. If the council forgets that, the frontier will remind it."]),
    ("Ulda", "Ulda Karrask", "Master of Imperial Works", "the Empire", False,
     ["Mind the scaffolding, Highness. Half this caldera is still being carved.",
      "The council wants a new aqueduct, a new arena and a new treasury vault. I have the stone for one."]),
    ("Halvana", "Halvana Pryce", "Governor of Meridia", "Meridia", False,
     ["Meridia sends its greetings, and its grain ships. We are neighbours across the water, Highness.",
      "The southern isles will back any proposal that keeps the sea lanes open. Remember that when you vote."]),
    ("Thrask", "Thrask Ur-Vashen", "King of Khar-Dumeth", "Khar-Dumeth", False,
     ["Prince of cows! The assessors bleed us all. Stand with Khar-Dumeth and they bleed less.",
      "At council I will demand the tribute be cut. Back me, and Khar-Dumeth remembers its friends."]),
    ("Vashka", "Vashka Tor-Ilun", "Queen of Tor-Ilun", "Tor-Ilun", False,
     ["The desert teaches patience, Highness. So does sitting through Imperial council.",
      "Tor-Ilun will vote with whoever offers copper prices we can live with. I am not sentimental."]),
    ("Ilsaveth", "Ilsaveth Anorai", "Queen of Velithra", "Velithra", False,
     ["Vaccaria. Green hills, deep wells and no navy. Charming.",
      "Velithra's merchants will sit on every side of every vote. That is what merchants are for."]),
    ("Oduvar", "Oduvar Brunnhak", "King of Karst Odun", "Karst Odun", False,
     ["Hm. A prince who looks you in the eye. Good. Karst Odun trusts that.",
      "We will sell steel to the Legions whatever the council decides. The council knows it, too."]),
    ("Marcellan", "Marcellan Dorr", "King of Lucerna", "Lucerna", False,
     ["Neighbour! Lucerna and Vaccaria should be closer friends. Your pastures and my granaries, eh?",
      "I will propose a road between our realms at council. Paid for by the Treasury, naturally."]),
]


def legacy_to_modern(img):
    """Convert a 64x32 skin to 64x64 exactly as Minecraft does: mirror the right leg and arm into the left slots."""
    img = img.convert("RGBA")
    if img.size == (64, 64):
        return img
    out = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    out.paste(img, (0, 0))
    moves = [((4, 16, 4, 4), (20, 48)), ((8, 16, 4, 4), (24, 48)), ((0, 20, 4, 12), (24, 52)), ((4, 20, 4, 12), (20, 52)),
             ((8, 20, 4, 12), (16, 52)), ((12, 20, 4, 12), (28, 52)),
             ((44, 16, 4, 4), (36, 48)), ((48, 16, 4, 4), (40, 48)), ((40, 20, 4, 12), (40, 52)), ((44, 20, 4, 12), (36, 52)),
             ((48, 20, 4, 12), (32, 52)), ((52, 20, 4, 12), (44, 52))]
    for (x, y, w, h), dst in moves:
        out.paste(ImageOps.mirror(img.crop((x, y, x + w, y + h))), dst)
    return out


def add_court(bp, rp, pack_dir, cast_json):
    cast = {c["name"]: c for c in json.load(open(cast_json))}
    # textures
    tdir = os.path.join(rp, "textures", "entity", NS, "court")
    os.makedirs(tdir, exist_ok=True)
    for i, (tag, full, title, realm, guard, lines) in enumerate(CHARS, 1):
        match = next((c for n, c in cast.items() if n.split()[0] == full.split()[0] or n.startswith(full.split()[0])), None)
        if match is None:
            match = next(c for n, c in cast.items() if tag in n)
        legacy_to_modern(Image.open(os.path.join(pack_dir, match["file"]))).save(os.path.join(tdir, "char_%02d.png" % i))
    # behaviour: copy the cow-folk entity and turn ranks into characters
    cow = json.load(open(os.path.join(bp, "entities", "cow_folk.json")))
    e = cow["minecraft:entity"]
    e["description"]["identifier"] = ENTITY
    e["components"]["minecraft:type_family"]["family"] = ["vaccaria", "courtier", "npc", "mob"]
    groups = {k: v for k, v in e["component_groups"].items() if not k.startswith(NS + ":rank_")}
    for i in range(1, len(CHARS) + 1):
        groups["%s:char_%d" % (NS, i)] = {"minecraft:variant": {"value": i}}
    e["component_groups"] = groups
    events = {k: v for k, v in e["events"].items() if not (k.startswith(NS + ":make_rank_") or k == NS + ":make_random")}
    for i, c in enumerate(CHARS, 1):
        role = NS + (":guard" if c[4] else ":civilian")
        events["%s:make_char_%d" % (NS, i)] = {"add": {"component_groups": ["%s:char_%d" % (NS, i), role, NS + ":awake", NS + ":council"]}}
    events["minecraft:entity_spawned"] = {"add": {"component_groups": [NS + ":char_1", NS + ":civilian", NS + ":awake", NS + ":council"]}}
    e["events"] = events
    json.dump(cow, open(os.path.join(bp, "entities", "courtier.json"), "w"), indent=1)
    # resources: same model and animations, a texture per character
    ce = json.load(open(os.path.join(rp, "entity", "cow_folk.entity.json")))
    d = ce["minecraft:client_entity"]["description"]
    d["identifier"] = ENTITY
    d["textures"] = {"char_%d" % i: "textures/entity/%s/court/char_%02d" % (NS, i) for i in range(1, len(CHARS) + 1)}
    d["render_controllers"] = ["controller.render.%s.courtier" % NS]
    d["spawn_egg"] = {"base_color": "#5a1f5c", "overlay_color": "#d8a23a"}
    json.dump(ce, open(os.path.join(rp, "entity", "courtier.entity.json"), "w"), indent=1)
    json.dump({"format_version": "1.8.0", "render_controllers": {"controller.render.%s.courtier" % NS: {
        "arrays": {"textures": {"Array.skins": ["Texture.char_%d" % i for i in range(1, len(CHARS) + 1)]}},
        "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
        "textures": ["Array.skins[math.clamp(query.variant - 1, 0, %d)]" % (len(CHARS) - 1)]}}},
        open(os.path.join(rp, "render_controllers", "courtier.render_controllers.json"), "w"), indent=1)
    with open(os.path.join(rp, "texts", "en_US.lang"), "a") as f:
        f.write("entity.%s.name=Courtier\nitem.spawn_egg.entity.%s.name=Spawn Courtier\n" % (ENTITY, ENTITY))
    # the whole court in a ring around you
    import math
    lines = ["# Summon the Imperial court: all sixteen named characters in a ring around you"]
    for i, c in enumerate(CHARS, 1):
        a = 2 * math.pi * (i - 1) / len(CHARS)
        lines.append('summon %s ~%d ~ ~%d 0 0 %s:make_char_%d "%s"' % (ENTITY, round(math.cos(a) * 6), round(math.sin(a) * 6), NS, i, c[0]))
    fdir = os.path.join(bp, "functions", NS)
    open(os.path.join(fdir, "court.mcfunction"), "w").write("\n".join(lines) + "\n")
    chars = {i: {"tag": c[0], "full": c[1], "title": c[2], "realm": c[3], "lines": c[5]} for i, c in enumerate(CHARS, 1)}
    return COURT_SCRIPT.replace("__CHARS__", json.dumps(chars))


COURT_SCRIPT = r'''
// ---- the Imperial court: named characters with their own lines ------------------------------------------
import { world as cw } from "@minecraft/server";
import { ActionFormData as CF } from "@minecraft/server-ui";

const CHARS = __CHARS__;

function talkCourt(player, e) {
  const n = e.getComponent("minecraft:variant")?.value ?? 1;
  const c = CHARS[n] ?? CHARS[1];
  if (!e.nameTag) { try { e.nameTag = c.tag; } catch (x) { } }
  const following = e.getDynamicProperty("vaccaria:follow") === player.id;
  new CF().title(c.tag)
    .body(`§7${c.full}, ${c.title}${c.realm !== "the Empire" ? " (" + c.realm + ")" : ""}§r\n\n${c.lines[0]}`)
    .button("What news of the council?")
    .button(following ? "Stay here" : "Walk with me")
    .button("Speak freely")
    .button("Farewell")
    .show(player).then((r) => {
      if (r.canceled || r.selection === 3) return;
      if (r.selection === 2) { speakFreely(player, { who: c.tag, kind: "courtier", variant: n }); return; }
      if (r.selection === 1) {
        if (following) { stopFollowing(e); notify(player, `§6${c.tag} returns to their post.`); }
        else { startFollowing(e, player); notify(player, `§6${c.tag} walks with you.`); }
        return;
      }
      new CF().title(c.tag).body(c.lines[1]).button("Thank you").show(player);
    });
}

cw.afterEvents.playerInteractWithEntity.subscribe((ev) => {
  if (ev.target?.typeId === "vaccaria:courtier" && ev.itemStack?.typeId !== "vaccaria:ledger") talkCourt(ev.player, ev.target);
});
'''
