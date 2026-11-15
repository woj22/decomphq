"""Authoring script for the fortress wings (owner request: corridors, private rooms, offices, chapel, refectory...).
Writes game/data/areas/*.json, npcs and dialogue. Re-run after editing: python3 tools/content/wings.py
Grid conventions: row 0 = far NE wall (doors 'D' allowed), col 0 = far NW wall, last row/col = near kerbs ('k', doors allowed).
"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "game", "data")
def W(rel, obj):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
def L(rel): return json.load(open(os.path.join(ROOT, rel)))

BASE_LEGEND = {"#": {"kind": "wall"}, "k": {"kind": "kerb"}, "D": {"kind": "door"}, ".": {"kind": "floor"},
 "B": {"kind": "prop", "prop": "brazier_0", "solid": True}, "S": {"kind": "prop", "prop": "shelf_books", "solid": True},
 "n": {"kind": "prop", "prop": "bed", "solid": True}, "w": {"kind": "prop", "prop": "washstand", "solid": True},
 "d": {"kind": "prop", "prop": "desk_clerk", "solid": True}, "e": {"kind": "prop", "prop": "desk_superior", "solid": True},
 "o": {"kind": "prop", "prop": "stool", "solid": False}, "l": {"kind": "prop", "prop": "lectern", "solid": True},
 "W": {"kind": "prop", "prop": "wardrobe", "solid": True}, "c": {"kind": "prop", "prop": "coffer", "solid": True},
 "T": {"kind": "prop", "prop": "long_table", "solid": True}, "=": {"kind": "prop", "prop": "bench_long", "solid": False},
 "p": {"kind": "prop", "prop": "pew", "solid": True}, "A": {"kind": "prop", "prop": "altar", "solid": True},
 "i": {"kind": "prop", "prop": "candle_stand", "solid": True}, "M": {"kind": "prop", "prop": "map_table", "solid": True},
 "H": {"kind": "prop", "prop": "throne", "solid": True}, "g": {"kind": "prop", "prop": "ledger_stack", "solid": True},
 "s": {"kind": "prop", "prop": "infirmary_screen", "solid": True}, "b": {"kind": "prop", "prop": "bookcase_low", "solid": True},
 "u": {"kind": "prop", "prop": "cauldron", "solid": True}, "x": {"kind": "prop", "prop": "chain_post", "solid": True},
 "R": {"kind": "prop", "prop": "brazier_hell", "solid": True}}

def blank(w, h):
    g = ["#" * w] + ["#" + "." * (w - 2) + "k" for _ in range(h - 2)] + ["k" * w]
    return [list(r) for r in g]
def put(g, x, y, ch): g[y][x] = ch
def rows(g): return ["".join(r) for r in g]

def area(aid, name, g, objects, spawns, decor=(), windows=(), amb="amb_chamber", floor="floor_flag", ambient=None, extra=None):
    d = {"id": aid, "name": name, "size": [len(g[0]), len(g)], "ambience": amb, "backdrop": "none",
         "grid": rows(g), "legend": BASE_LEGEND, "floor": floor, "windows": list(windows), "decor": list(decor),
         "objects": objects, "spawns": spawns, "zones": {}, "ambient": ambient or {"desk_clerks": [], "staff": [], "flows": []}}
    if extra: d.update(extra)
    W("areas/%s.json" % aid, d)

def door(oid, cell, use, to_area, to_spawn, **kw):
    o = {"id": oid, "type": "door", "cell": list(cell), "use_cell": list(use), "style": kw.pop("style", "plain"),
         "to": {"area": to_area, "spawn": to_spawn}}
    o.update(kw); return o

def dlg(i, speaker, lines, effects=None, choices=None):
    nodes = {}
    for k, t in enumerate(lines):
        nodes["n%d" % (k + 1)] = {"speaker": speaker, "text": t, "next": "n%d" % (k + 2) if k + 1 < len(lines) else "end"}
    if effects: nodes["n%d" % len(lines)]["effects"] = effects
    W("dialogue/%s.json" % i, {"id": i, "start": "n1", "nodes": nodes})

NIGHT = [22, 6]; DAY = [6, 22]
dlg("dlg_asleep", "narrator", ["Asleep, and breathing out of habit. You let them be."])
dlg("dlg_occupied", "narrator", ["A brass card on the door: OCCUPIED. Someone inside is pretending very hard to be out."])

# ============================================================== LOWER CLOISTER (west of the Court)
g = blank(22, 7)
for x in (3, 8, 13, 18): put(g, x, 0, "D")
put(g, 0, 3, "D"); put(g, 21, 3, "D")
for x in (2, 6, 10, 14, 19): put(g, x, 1, "i")
put(g, 1, 5, "B"); put(g, 20, 5, "B")
area("area_lower_cloister", "The Lower Cloister", g, [
    door("door_lc_court", (21, 3), (20, 3), "area_clerks_court", "from_cells"),
    door("door_lc_cells", (3, 0), (3, 1), "area_deferral_cells", "from_court"),
    door("door_lc_infirmary", (8, 0), (8, 1), "area_infirmary", "from_cloister"),
    door("door_lc_chapel", (13, 0), (13, 1), "area_chapel", "from_cloister"),
    door("door_lc_refectory", (18, 0), (18, 1), "area_refectory", "from_cloister"),
    door("door_lc_undercroft", (0, 3), (1, 3), "area_undercroft", "from_cloister",
         conditions=[{"op": "flag", "id": "flag_undercroft_open"}], locked_dialogue="dlg_undercroft_locked")],
    {"default": [20, 3], "from_court": [20, 3], "from_cells": [3, 1], "from_infirmary": [8, 1], "from_chapel": [13, 1],
     "from_refectory": [18, 1], "from_undercroft": [1, 3]},
    decor=[{"sprite": "light_pool_gold", "cell": [x, 2]} for x in (2, 6, 10, 14, 19)] + [{"sprite": "banner_red", "cell": [11, 0]}],
    amb="amb_court",
    ambient={"desk_clerks": [], "flows": [],
             "staff": [{"sprite": "chr_clerk_grey", "count": 2, "rect": [1, 2, 20, 5], "hours": [7, 22]},
                       {"sprite": "chr_guard", "count": 1, "rect": [1, 2, 20, 5], "hours": [6, 22]},
                       {"sprite": "chr_guard_night", "count": 2, "rect": [1, 2, 20, 5], "hours": [22, 6]},
                       {"sprite": "chr_clerk_lilac", "count": 2, "rect": [12, 2, 20, 5], "hours": [[11, 13], [17, 20]]}]})
dlg("dlg_undercroft_locked", "narrator", ["A low iron door, chained. Someone has scratched a word into the lock plate: SMOULDER."])

# ============================================================== INFIRMARY (the healer lives here)
g = blank(12, 8)
for x in (2, 5, 8): put(g, x, 1, "n"); put(g, x, 3, "s")
put(g, 10, 1, "u"); put(g, 10, 5, "W"); put(g, 1, 5, "l")
put(g, 5, 7, "D")
area("area_infirmary", "The Infirmary", g, [
    door("door_inf_cloister", (5, 7), (5, 6), "area_lower_cloister", "from_infirmary"),
    {"id": "obj_infirmarian", "type": "npc", "npc": "npc_infirmarian", "cell": [7, 5], "facing": "sw", "use_cell": [7, 6], "hours": DAY},
    {"id": "obj_infirmarian_sleep", "type": "npc", "npc": "npc_infirmarian", "cell": [8, 1], "facing": "sw", "use_cell": [8, 2],
     "hours": NIGHT, "asleep": True}],
    {"default": [5, 6], "from_cloister": [5, 6]},
    decor=[{"sprite": "light_pool_gold", "cell": [5, 4]}], windows=[{"cell": [0, 3], "glass": "gold"}], amb="amb_records",
    ambient={"desk_clerks": [], "flows": [], "staff": [{"sprite": "chr_soul_1", "count": 1, "rect": [1, 4, 9, 5], "always": True}]})
W("npcs/npc_infirmarian.json", {"id": "npc_infirmarian", "name": "Sister Bettony Cole", "title": "Infirmarian", "sprite": "chr_clerk_lilac",
  "portrait": "por_marrow", "dialogue": [{"id": "dlg_infirmarian"}]})
W("dialogue/dlg_infirmarian.json", {"id": "dlg_infirmarian", "start": "n1", "nodes": {
  "n1": {"speaker": "npc_infirmarian", "text": "Torn again? Souls do not bleed, but they fray. Sit. Two obols, and do try to keep your edges on.", "next": "n2"},
  "n2": {"speaker": "player", "choices": [
     {"text": "Mend me (2 obols).", "next": "mend", "conditions": [{"op": "stat_gte", "id": "purse", "value": 2}]},
     {"text": "Just visiting.", "next": "end"}]},
  "mend": {"speaker": "npc_infirmarian", "text": "There. Whole-ish. If you get dragged in from the Gate again I am charging double.",
           "effects": [{"op": "add_stat", "id": "purse", "value": -2}, {"op": "heal"}], "next": "end"}}})

# ============================================================== CHAPEL OF NEITHER
g = blank(12, 9)
put(g, 5, 1, "A"); put(g, 3, 1, "i"); put(g, 7, 1, "i")
for y in (3, 5):
    for x in (2, 3, 4, 7, 8, 9): put(g, x, y, "p")
put(g, 5, 8, "D")
area("area_chapel", "The Chapel of Neither", g, [
    door("door_chapel_cloister", (5, 8), (5, 7), "area_lower_cloister", "from_chapel"),
    {"id": "obj_altar", "type": "inspect", "cell": [5, 1], "use_cell": [5, 2], "dialogue": "dlg_altar", "verb": "Pray"}],
    {"default": [5, 7], "from_cloister": [5, 7]},
    decor=[{"sprite": "light_pool_gold", "cell": [4, 2]}, {"sprite": "light_pool_red", "cell": [6, 2]},
           {"sprite": "banner_gold", "cell": [2, 0]}, {"sprite": "banner_red", "cell": [9, 0]}],
    windows=[{"cell": [0, 3], "glass": "gold"}, {"cell": [10, 0], "glass": "red"}], amb="amb_chamber",
    ambient={"desk_clerks": [], "flows": [],
             "staff": [{"sprite": "chr_soul_2", "count": 2, "rect": [1, 6, 10, 7], "always": True, "pause": [6, 14]},
                       {"sprite": "chr_clerk_grey", "count": 1, "rect": [1, 6, 10, 7], "hours": [6, 9]}]})
dlg("dlg_altar", "narrator", ["The altar is half gold cloth, half red. Neither side would pay for the whole thing.",
    "Someone has left a candle, a prayer and a filing number. You add nothing. It feels like enough."], [{"op": "heal"}])

# ============================================================== REFECTORY (meals: 12-14 and 18-21)
g = blank(16, 10)
for y in (2, 5):
    for x in range(3, 13): put(g, x, y, "T")
    for x in range(3, 13): put(g, x, y + 1, "=")
put(g, 1, 8, "u"); put(g, 14, 1, "W"); put(g, 1, 1, "B")
meal = [[12, 14], [18, 21]]
put(g, 7, 9, "D")
area("area_refectory", "The Refectory", g, [
    door("door_ref_cloister", (7, 9), (7, 8), "area_lower_cloister", "from_refectory"),
    {"id": "obj_wren_supper", "type": "npc", "npc": "npc_wren", "cell": [6, 3], "facing": "ne", "use_cell": [6, 4], "hours": [[12, 13], [18, 21]]},
    {"id": "obj_grist_supper", "type": "npc", "npc": "npc_grist", "cell": [10, 6], "facing": "ne", "use_cell": [10, 7], "hours": [18, 22]},
    {"id": "obj_cook", "type": "inspect", "cell": [1, 8], "use_cell": [2, 8], "dialogue": "dlg_cook", "verb": "Eat"}],
    {"default": [7, 8], "from_cloister": [7, 8]},
    decor=[{"sprite": "light_pool_gold", "cell": [x, 4]} for x in (4, 8, 12)] + [{"sprite": "banner_red", "cell": [7, 0]}],
    windows=[{"cell": [4, 0], "glass": "gold"}, {"cell": [11, 0], "glass": "gold"}, {"cell": [0, 5], "glass": "gold"}],
    amb="amb_hall",
    ambient={"desk_clerks": [], "flows": [],
             "staff": [{"sprite": "chr_clerk_grey", "count": 6, "rect": [3, 3, 12, 7], "hours": meal, "seated": True},
                       {"sprite": "chr_clerk_lilac", "count": 3, "rect": [3, 3, 12, 7], "hours": meal, "seated": True},
                       {"sprite": "chr_guard", "count": 2, "rect": [3, 3, 12, 7], "hours": [18, 21], "seated": True},
                       {"sprite": "chr_archivist", "count": 1, "rect": [1, 1, 14, 8], "hours": meal},
                       {"sprite": "chr_clerk_grey", "count": 1, "rect": [1, 1, 14, 8], "hours": [9, 12]}]})
dlg("dlg_cook", "narrator", ["The cauldron holds the Refectory's only dish: a grey broth the menu calls 'Remembrance'.",
    "It tastes of whatever you last ate alive. Yours is bread and pears. You feel steadier."], [{"op": "heal"}])

# ============================================================== UNDERCROFT (story; locked for now)
g = blank(14, 8)
for x in (3, 7, 11): put(g, x, 2, "x")
put(g, 12, 6, "R")
put(g, 13, 4, "D")
area("area_undercroft", "The Undercroft", g, [
    door("door_uc_cloister", (13, 4), (12, 4), "area_lower_cloister", "from_undercroft"),
    {"id": "obj_smoulder", "type": "npc", "npc": "npc_smoulder", "cell": [4, 5], "facing": "se", "use_cell": [5, 5]}],
    {"default": [12, 4], "from_cloister": [12, 4]}, decor=[{"sprite": "light_pool_red", "cell": [6, 4]}], amb="amb_hell",
    ambient={"desk_clerks": [], "flows": [], "staff": [{"sprite": "chr_soul_3", "count": 4, "rect": [1, 3, 10, 6], "always": True}]})

# ============================================================== RESIDENCE GALLERY + private rooms
g = blank(26, 7)
room_doors = [(2, "marrow"), (5, "wren"), (8, "grist"), (11, "dorcas"), (14, "ysolde"), (17, "quill"), (20, "player"), (23, "dormitory")]
for x, _ in room_doors: put(g, x, 0, "D")
put(g, 0, 3, "D")
for x in (3, 9, 15, 21): put(g, x, 1, "i")
objs = [door("door_res_court", (0, 3), (1, 3), "area_clerks_court", "from_dorm")]
spawns = {"default": [1, 3], "from_court": [1, 3]}
for x, who in room_doors:
    target = "area_dormitory" if who == "dormitory" else "area_room_" + who
    objs.append(door("door_res_" + who, (x, 0), (x, 1), target, "from_gallery"))
    spawns["from_" + who] = [x, 1]
for i, x in enumerate((4, 9, 14, 19)):
    objs.append({"id": "obj_occupied_%d" % i, "type": "inspect", "cell": [x, 6], "use_cell": [x, 5], "dialogue": "dlg_occupied", "verb": "Knock"})
area("area_residences", "The Residence Gallery", g, objs, spawns,
     decor=[{"sprite": "light_pool_gold", "cell": [x, 2]} for x in (3, 9, 15, 21)] + [{"sprite": "banner_red", "cell": [12, 0]}],
     amb="amb_chamber",
     ambient={"desk_clerks": [], "flows": [],
              "staff": [{"sprite": "chr_clerk_grey", "count": 2, "rect": [1, 2, 24, 5], "hours": [[6, 9], [20, 23]]},
                        {"sprite": "chr_clerk_lilac", "count": 1, "rect": [1, 2, 24, 5], "hours": [[6, 9], [20, 23]]},
                        {"sprite": "chr_guard_night", "count": 1, "rect": [1, 2, 24, 5], "hours": [23, 6]}]})
# the old dormitory now opens onto the gallery
d = L("areas/area_dormitory.json")
for o in d["objects"]:
    if o["id"] == "door_dorm_court": o["to"] = {"area": "area_residences", "spawn": "from_dormitory"}
d["spawns"]["from_gallery"] = d["spawns"].get("from_court", [1, 4])
d["name"] = "The Common Dormitory"
W("areas/area_dormitory.json", d)

def private_room(who, title, npc, sprite_note, keepsake, keepsake_lines, extra_props=(), night_hours=NIGHT, day_npc=False, rug="rug_red"):
    g = blank(8, 7)
    put(g, 1, 1, "n"); put(g, 3, 1, "W"); put(g, 6, 1, "S"); put(g, 6, 4, "d"); put(g, 1, 4, "w")
    for (x, y, ch) in extra_props: put(g, x, y, ch)
    put(g, 3, 6, "D")
    objs = [door("door_room_%s_out" % who, (3, 6), (3, 5), "area_residences", "from_" + who),
            {"id": "obj_keepsake_" + who, "type": "inspect", "cell": [6, 4], "use_cell": [5, 4], "dialogue": "dlg_keepsake_" + who, "verb": "Read"}]
    if npc:
        objs.append({"id": "obj_%s_asleep" % who, "type": "npc", "npc": npc, "cell": [1, 1], "facing": "se", "use_cell": [2, 2],
                     "hours": night_hours, "asleep": True})
    area("area_room_" + who, title, g, objs, {"default": [3, 5], "from_gallery": [3, 5]},
         decor=[{"sprite": rug, "cell": [3, 3]}, {"sprite": "light_pool_gold", "cell": [5, 4]}, {"sprite": "wall_torch_x", "cell": [5, 0]}],
         windows=[{"cell": [2, 0], "glass": "gold"}], amb="amb_records")
    dlg("dlg_keepsake_" + who, "narrator", keepsake_lines)

private_room("marrow", "Marrow's Room", "npc_marrow", "", "file", [
    "A single file in the desk drawer, worn soft at the corners. The name has been read so often it is almost gone.",
    "A note in Marrow's hand: 'Sent the wrong way, 1702. Every day since, I check twice.'"])
private_room("wren", "Wren's Room", "npc_wren", "", "cribs", [
    "Under the mattress: a sheaf of slips, each with a soul's name and a verdict, in a hand that is not Wren's.",
    "The ink is violet. You put them back exactly as you found them."])
private_room("grist", "Grist's Room", "npc_grist", "", "papers", [
    "Dominion conscription papers, folded small. 'H. Grist, Pit Levy, 3rd Draft.' Stamped DESERTER in red, then DEFERRED in black.",
    "Beside them, a child's carved horse. Grist's hands are not made for carving. He kept at it anyway."])
private_room("dorcas", "Dorcas Ferrule's Room", "npc_registrar", "", "register", [
    "A private register of every soul Dorcas has ever called forward. Forty thousand names. Each has a tiny tick.",
    "The ticks mean 'I said their name kindly'. There are no gaps."])
private_room("ysolde", "Ysolde Vane's Room", "npc_thaumaturge", "", "grimoire", [
    "A grimoire stamped UNAUDITED on every page, in Ysolde's own hand. It is not a confession. It is a boast.",
    "Margin note: 'Thrace asked for a binding that writes in a dead man's hand. I said no. Someone else said yes.'"],
    extra_props=[(4, 4, "u")])
private_room("quill", "Malphas Quill's Room", "npc_gatekeeper", "", "ledger", [
    "A debt-book bound in something you decide not to identify. Every debt in it is paid, struck through, and initialled.",
    "One page is headed RECLAIMERS - UNAUTHORISED. It is very long."], night_hours=[6, 12], rug="rug_red")
# the player's own room: sleep here
g = blank(8, 7)
put(g, 1, 1, "n"); put(g, 3, 1, "W"); put(g, 6, 4, "d"); put(g, 1, 4, "w"); put(g, 6, 1, "b"); put(g, 3, 6, "D")
area("area_room_player", "Your Room", g, [
    door("door_room_player_out", (3, 6), (3, 5), "area_residences", "from_player"),
    {"id": "obj_my_bed", "type": "inspect", "cell": [1, 1], "use_cell": [2, 2], "dialogue": "dlg_sleep", "verb": "Sleep"},
    {"id": "obj_own_file", "type": "inspect", "cell": [6, 4], "use_cell": [5, 4], "dialogue": "dlg_own_file", "verb": "Read"}],
    {"default": [3, 5], "from_gallery": [3, 5]},
    decor=[{"sprite": "rug_gold", "cell": [3, 3]}, {"sprite": "light_pool_gold", "cell": [5, 4]}], windows=[{"cell": [2, 0], "glass": "gold"}],
    amb="amb_records")
dlg("dlg_own_file", "narrator", ["On your desk, delivered without a covering note: your own file. Every line in black ink.",
    "Stamped DEFERRED, like everyone's here. You do not open it. Not yet."])
# the dormitory cot stays for anyone who prefers it; the player's bed moves to Your Room
d = L("areas/area_dormitory.json")
d["objects"] = [o for o in d["objects"] if o["id"] not in ("obj_my_bed", "obj_spare_cot")]
d["objects"].append({"id": "obj_spare_cot", "type": "inspect", "cell": [3, 1], "use_cell": [3, 2], "dialogue": "dlg_sleep", "verb": "Sleep"})
W("areas/area_dormitory.json", d)

# Odalys's hideaway, off the Back Room
g = blank(7, 6)
put(g, 1, 1, "n"); put(g, 4, 1, "g"); put(g, 5, 3, "d"); put(g, 0, 3, "D")
area("area_room_odalys", "Odalys's Hideaway", g, [
    door("door_odalys_back", (0, 3), (1, 3), "area_back_room", "from_odalys"),
    {"id": "obj_odalys_room", "type": "companion", "npc": "npc_odalys", "cell": [3, 3], "facing": "sw", "use_cell": [3, 4], "verb": "Talk", "hours": NIGHT},
    {"id": "obj_keepsake_odalys", "type": "inspect", "cell": [5, 3], "use_cell": [4, 3], "dialogue": "dlg_keepsake_odalys", "verb": "Read"}],
    {"default": [1, 3], "from_back": [1, 3]},
    decor=[{"sprite": "light_pool_gold", "cell": [3, 2]}, {"sprite": "rug_red", "cell": [3, 3]}], amb="amb_records")
dlg("dlg_keepsake_odalys", "narrator", ["A copied file in violet ink: 'Wick, Hester. Amended: Ember Gate.' Odalys's sister.",
    "Below it, in black, in Odalys's careful copying hand, the original. Hester went to Heaven. Then someone changed it."])
b = L("areas/area_back_room.json")
grid = [list(r) for r in b["grid"]]
grid[4][7] = "D"; b["grid"] = ["".join(r) for r in grid]
b["objects"] = [o for o in b["objects"] if o["id"] != "door_back_odalys"]
b["objects"].append(door("door_back_odalys", (7, 4), (6, 4), "area_room_odalys", "from_back"))
b["spawns"]["from_odalys"] = [6, 4]
for o in b["objects"]:
    if o["id"] == "obj_odalys": o["hours"] = DAY  # by day she sits in the Back Room; at night she is in her hideaway... or the meeting
W("areas/area_back_room.json", b)

# ============================================================== UPPER CLOISTER (offices of the people running Purgatory)
g = blank(24, 7)
for x in (3, 8, 13, 18): put(g, x, 0, "D")
put(g, 0, 3, "D"); put(g, 23, 3, "D")
for x in (2, 6, 11, 16, 21): put(g, x, 1, "i")
area("area_upper_cloister", "The Upper Cloister", g, [
    door("door_uc_chamber", (23, 3), (22, 3), "area_adjudicator_chamber", "from_cloister"),
    door("door_uc_provost", (3, 0), (3, 1), "area_office_provost", "from_cloister"),
    door("door_uc_auditor", (8, 0), (8, 1), "area_office_auditor", "from_cloister"),
    door("door_uc_treasury", (13, 0), (13, 1), "area_treasury", "from_cloister"),
    door("door_uc_chancellor", (18, 0), (18, 1), "area_office_chancellor", "from_cloister",
         conditions=[{"op": "rank_gte", "value": 5}], locked_dialogue="dlg_chancellor_locked", style="gilt"),
    door("door_uc_diplomatic", (0, 3), (1, 3), "area_diplomatic", "from_cloister")],
    {"default": [22, 3], "from_chamber": [22, 3], "from_provost": [3, 1], "from_auditor": [8, 1], "from_treasury": [13, 1],
     "from_chancellor": [18, 1], "from_diplomatic": [1, 3]},
    decor=[{"sprite": "light_pool_gold", "cell": [x, 2]} for x in (2, 6, 11, 16, 21)] + [{"sprite": "banner_gold", "cell": [10, 0]},
           {"sprite": "banner_red", "cell": [15, 0]}],
    amb="amb_chamber",
    ambient={"desk_clerks": [], "flows": [],
             "staff": [{"sprite": "chr_clerk_lilac", "count": 2, "rect": [1, 2, 22, 5], "hours": [7, 20]},
                       {"sprite": "chr_guard", "count": 2, "rect": [1, 2, 22, 5], "hours": [6, 22]},
                       {"sprite": "chr_guard_night", "count": 2, "rect": [1, 2, 22, 5], "hours": [22, 6]}]})
dlg("dlg_chancellor_locked", "narrator", ["Gilt doors, sealed with a wax disc the size of a plate. THE CHAIR IS VACANT. ADMITTANCE BY APPOINTMENT OF THE PRINCIPAL."])
# Chamber gets a west door to the Upper Cloister
c = L("areas/area_adjudicator_chamber.json")
grid = [list(r) for r in c["grid"]]; grid[7][0] = "D"; c["grid"] = ["".join(r) for r in grid]
c["windows"] = [w for w in c["windows"] if w["cell"] != [0, 7]]
c["objects"] = [o for o in c["objects"] if o["id"] != "door_chamber_cloister"]
c["objects"].append(door("door_chamber_cloister", (0, 7), (1, 7), "area_upper_cloister", "from_chamber"))
c["spawns"]["from_cloister"] = [1, 7]
W("areas/area_adjudicator_chamber.json", c)

def office(aid, title, who_obj, props, keepsake_id, keepsake_lines, w=12, h=9, back_spawn="from_cloister", back_area="area_upper_cloister",
           back_from=None, rug="rug_red", banners=("banner_red",), amb="amb_chamber", extra_objs=(), extra=None, ambient=None):
    g = blank(w, h)
    for (x, y, ch) in props: put(g, x, y, ch)
    dx = w // 2
    put(g, dx, h - 1, "D")
    objs = [door(aid + "_out", (dx, h - 1), (dx, h - 2), back_area, back_from)]
    if who_obj: objs += who_obj
    if keepsake_id:
        objs.append({"id": keepsake_id, "type": "inspect", "cell": keepsake_lines[0], "use_cell": keepsake_lines[1],
                     "dialogue": "dlg_" + keepsake_id, "verb": "Read"})
        dlg("dlg_" + keepsake_id, "narrator", keepsake_lines[2])
    objs += list(extra_objs)
    area(aid, title, g, objs, {"default": [dx, h - 2], back_spawn: [dx, h - 2]},
         decor=[{"sprite": rug, "cell": [dx, h // 2]}, {"sprite": "light_pool_gold", "cell": [dx, 3]}] +
               [{"sprite": b, "cell": [2 + 4 * i, 0]} for i, b in enumerate(banners)],
         windows=[{"cell": [w - 3, 0], "glass": "gold"}, {"cell": [0, 3], "glass": "gold"}], amb=amb, extra=extra,
         ambient=ambient)

office("area_office_provost", "The Lord Provost's Office",
       [{"id": "obj_provost", "type": "npc", "npc": "npc_provost", "cell": [6, 3], "facing": "sw", "use_cell": [6, 5], "hours": [9, 18]}],
       [(6, 4, "e"), (2, 1, "S"), (3, 1, "S"), (9, 1, "W"), (10, 5, "c"), (1, 6, "b")],
       "obj_provost_tray", [[10, 5], [9, 5], ["The Lord Provost's in-tray. Every document is signed. None appears to have been read.",
       "Third from the top, signed with a flourish: all Room 0 post to go 'direct to the Auditor-General, unopened'."]],
       back_from="from_provost", banners=("banner_gold", "banner_red"))
office("area_office_auditor", "The Auditor-General's Office",
       [{"id": "obj_thrace", "type": "npc", "npc": "npc_thrace", "cell": [6, 3], "facing": "sw", "use_cell": [6, 5], "hours": [7, 21]}],
       [(6, 4, "e"), (1, 1, "S"), (2, 1, "S"), (3, 1, "S"), (9, 1, "S"), (10, 1, "S"), (10, 5, "g"), (1, 5, "g")],
       "obj_auditor_shelf", [[10, 5], [9, 5], ["Ledgers, perfectly kept. The Auditor-General's public books balance to the soul.",
       "The shelf behind the desk is a fraction too deep. A draught comes from it. It smells faintly of ink."]],
       back_from="from_auditor", banners=("banner_red",), rug="rug_red")
office("area_treasury", "The Bursar's Treasury",
       [{"id": "obj_bursar", "type": "npc", "npc": "npc_bursar", "cell": [6, 3], "facing": "sw", "use_cell": [6, 5], "hours": [8, 17]}],
       [(6, 4, "d"), (1, 1, "c"), (2, 1, "c"), (3, 1, "c"), (9, 1, "c"), (10, 1, "c"), (10, 5, "g")],
       None, None, back_from="from_treasury", banners=("banner_gold",), rug="rug_gold")
office("area_office_chancellor", "The High Chancellor's Office", [],
       [(6, 2, "H"), (2, 1, "S"), (10, 1, "S"), (2, 5, "M"), (10, 5, "b")],
       "obj_chair", [[6, 2], [6, 3], ["The Chair. Black wood, gold leaf, worn at the arms by hands that have not touched it in decades.",
       "On the seat, a single file. Your name is on it."]], w=13, h=9, back_from="from_chancellor",
       banners=("banner_gold", "banner_red"), rug="rug_gold")

# ============================================================== DIPLOMATIC QUARTER + legations
g = blank(16, 7)
put(g, 4, 0, "D"); put(g, 11, 0, "D"); put(g, 15, 3, "D")
put(g, 2, 1, "i"); put(g, 8, 1, "i"); put(g, 13, 1, "i")
area("area_diplomatic", "The Diplomatic Quarter", g, [
    door("door_dq_cloister", (15, 3), (14, 3), "area_upper_cloister", "from_diplomatic"),
    door("door_dq_auric", (4, 0), (4, 1), "area_legation_auric", "from_quarter", style="gilt"),
    door("door_dq_dominion", (11, 0), (11, 1), "area_legation_dominion", "from_quarter", style="ember")],
    {"default": [14, 3], "from_cloister": [14, 3], "from_auric": [4, 1], "from_dominion": [11, 1]},
    decor=[{"sprite": "banner_gold", "cell": [2, 0]}, {"sprite": "banner_gold", "cell": [6, 0]}, {"sprite": "banner_red", "cell": [9, 0]},
           {"sprite": "banner_red", "cell": [13, 0]}, {"sprite": "light_pool_gold", "cell": [4, 2]}, {"sprite": "light_pool_red", "cell": [11, 2]}],
    amb="amb_chamber",
    ambient={"desk_clerks": [], "flows": [], "staff": [{"sprite": "chr_ashgrove", "count": 1, "rect": [1, 2, 7, 5], "hours": [9, 12]},
                                                        {"sprite": "chr_guard", "count": 2, "rect": [1, 2, 14, 5], "always": True}]})
office("area_legation_auric", "The Auric Legation",
       [{"id": "obj_ashgrove", "type": "npc", "npc": "npc_ashgrove", "cell": [4, 3], "facing": "sw", "use_cell": [4, 5], "hours": [8, 20]},
        {"id": "obj_vael", "type": "npc", "npc": "npc_vael", "cell": [8, 2], "facing": "sw", "use_cell": [8, 4], "hours": [10, 16],
         "visible_if": [{"op": "rank_gte", "value": 3}]}],
       [(4, 4, "d"), (2, 1, "i"), (10, 1, "i"), (1, 5, "b"), (10, 5, "b")],
       None, None, back_spawn="from_quarter", back_area="area_diplomatic", back_from="from_auric", banners=("banner_gold", "banner_gold"),
       rug="rug_gold")
office("area_legation_dominion", "The Dominion Legation",
       [{"id": "obj_crake", "type": "npc", "npc": "npc_crake", "cell": [6, 3], "facing": "sw", "use_cell": [6, 5], "hours": [6, 23]}],
       [(6, 4, "e"), (1, 1, "R"), (10, 1, "R"), (1, 5, "S"), (10, 5, "g")],
       None, None, back_spawn="from_quarter", back_area="area_diplomatic", back_from="from_dominion", banners=("banner_red", "banner_red"),
       amb="amb_hell")
# Furnace Guild Counting-House, off the Ember Gate
office("area_counting_house", "The Furnace Guild Counting-House",
       [{"id": "obj_glut", "type": "npc", "npc": "npc_glut", "cell": [6, 3], "facing": "sw", "use_cell": [6, 5], "hours": [[20, 24], [0, 4]],
         "visible_if": [{"op": "rank_gte", "value": 3}]}],
       [(6, 4, "e"), (1, 1, "R"), (10, 1, "R"), (1, 5, "c"), (10, 5, "c"), (2, 1, "g")],
       "obj_guild_ledger", [[2, 1], [2, 2], ["The Guild's day-book. Entries in red: 'Souls owed by the Chancery under the Compact.'",
       "The column of numbers matches, to the soul, the violet-ink files you have found."]],
       back_spawn="from_gate", back_area="area_ember_gate", back_from="from_counting", banners=("banner_red",), amb="amb_hell",
       ambient={"desk_clerks": [], "flows": [], "staff": [{"sprite": "chr_demon", "count": 2, "rect": [2, 2, 9, 6], "hours": [[20, 24], [0, 4]]}]})
e = L("areas/area_ember_gate.json")
grid = [list(r) for r in e["grid"]]; grid[6][0] = "D"; e["grid"] = ["".join(r) for r in grid]
e["objects"] = [o for o in e["objects"] if o["id"] != "door_ember_counting"]
e["objects"].append(door("door_ember_counting", (0, 6), (1, 6), "area_counting_house", "from_gate", style="ember"))
e["spawns"]["from_counting"] = [1, 6]
W("areas/area_ember_gate.json", e)

# ============================================================== retarget the Court's doors to the new corridors
c = L("areas/area_clerks_court.json")
for o in c["objects"]:
    if o["id"] == "door_court_cells": o["to"] = {"area": "area_lower_cloister", "spawn": "from_court"}
    if o["id"] == "door_court_dorm": o["to"] = {"area": "area_residences", "spawn": "from_court"}
W("areas/area_clerks_court.json", c)
ce = L("areas/area_deferral_cells.json")
for o in ce["objects"]:
    if o["id"] == "door_cells_court": o["to"] = {"area": "area_lower_cloister", "spawn": "from_cells"}
ce["spawns"]["from_court"] = ce["spawns"].get("from_court", [1, 5])
W("areas/area_deferral_cells.json", ce)

# ============================================================== people (routines: work by day, own bed by night)
def npc(nid, name, title, sprite, portrait, dialogue):
    W("npcs/%s.json" % nid, {"id": nid, "name": name, "title": title, "sprite": sprite, "portrait": portrait, "dialogue": dialogue})
npc("npc_provost", "Hadrian Quill", "Lord Provost, acting head of the Chancery", "chr_provost", "por_provost", [{"id": "dlg_provost"}])
npc("npc_thrace", "Corvin Thrace", "Auditor-General", "chr_thrace", "por_thrace", [{"id": "dlg_thrace"}])
npc("npc_bursar", "Ambrose Tallow", "Bursar", "chr_clerk_grey", "por_registrar", [{"id": "dlg_bursar"}])
npc("npc_ashgrove", "Celandine Ashgrove", "Auric Envoy to Limen", "chr_ashgrove", "por_ashgrove", [{"id": "dlg_ashgrove"}])
npc("npc_vael", "Seraphine Vael", "Archon of the Lustrants", "chr_vael", "por_vael", [{"id": "dlg_vael"}])
npc("npc_crake", "Lady Malvolia Crake", "Dominion Ambassador, Warden of Debt", "chr_crake", "por_crake", [{"id": "dlg_crake"}])
npc("npc_glut", "Baron Mordecai Glut", "Master of the Furnace Guild", "chr_glut", "por_glut", [{"id": "dlg_glut"}])
npc("npc_smoulder", "Ezekiel Smoulder", "Reclaimer advocate", "chr_smoulder", "por_smoulder", [{"id": "dlg_smoulder"}])
dlg("dlg_provost", "npc_provost", ["Adjudicator! Splendid. Everything is splendid. Is it? It is. Sign here, would you, while you're up.",
    "Room 0? Never heard of it. Well, heard of it. Signed for it, possibly. One signs so much."])
dlg("dlg_thrace", "npc_thrace", ["Adjudicator. Your accuracy is noted. Accuracy is a kind of mercy, in a place like this.",
    "The numbers must come out right. Everything else is sentiment, and sentiment started a war once."])
dlg("dlg_bursar", "npc_bursar", ["Pay is issued at the shift ledger, Adjudicator, not by me. I merely count it. Lovingly."])
dlg("dlg_ashgrove", "npc_ashgrove", ["Adjudicator - I remember your name, you see, it's my one gift. The Concord admires your verdicts.",
    "Admiration is a currency, too. Do come and spend some, when you have a moment."])
dlg("dlg_vael", "npc_vael", ["You are the one who stamps so carefully. Careful is good. Careful is countable.",
    "Heaven is not a crowd, Adjudicator. It is a choir. A choir must be kept in tune."])
dlg("dlg_crake", "npc_crake", ["Adjudicator. The Dominion keeps its debts honestly. Not everyone who wears our colours does.",
    "If you ever find the Furnace Guild's books, bring them here before you bring them anywhere else."])
dlg("dlg_glut", "npc_glut", ["Come in, come in! Warm, isn't it? Everything's warm down here. Brandy? It's been dead for centuries but it travels.",
    "Hands, Adjudicator. The Guild is always short of hands. I'm sure we can come to an arrangement."])
dlg("dlg_smoulder", "npc_smoulder", ["You found us. Please - keep your voice down. Every soul here was 'paid up' and sent back. I couldn't just leave them.",
    "When you're ready to bring down the Compact, they'll speak. All of them. They remember who wrote them down."])
# existing characters get beds: day posts stay as they are (they already sleep at night); add their asleep placements via rooms above.
print("wings written")
