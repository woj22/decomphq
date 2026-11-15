"""Acts III-V (owner request: the storyline continues to boss battles against the people running Purgatory).
Run after wings.py: python3 tools/content/story_acts.py
"""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "game", "data")
def W(rel, obj): open(os.path.join(ROOT, rel), "w").write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
def L(rel): return json.load(open(os.path.join(ROOT, rel)))
def F(f): return {"op": "flag", "id": f}
def NF(f): return {"op": "not_flag", "id": f}
NIGHT = {"op": "is_night"}
def RANK(n): return {"op": "rank_gte", "value": n}
def NOT(c): return {"op": "not", "of": c}
def card(t, x): return {"op": "show_card", "title": t, "text": x}
def obj(i): return {"op": "set_objective", "id": i}
def setf(f): return {"op": "set_flag", "id": f, "value": True}
def lines(i, spk, ls, effects=None):
    nodes = {}
    for k, t in enumerate(ls):
        assert len(t) <= 140, (i, len(t), t)
        nodes["n%d" % (k + 1)] = {"speaker": spk, "text": t, "next": "n%d" % (k + 2) if k + 1 < len(ls) else "end"}
    if effects: nodes["n%d" % len(ls)]["effects"] = effects
    W("dialogue/%s.json" % i, {"id": i, "start": "n1", "nodes": nodes})
def prepend(npc, entries):
    n = L("npcs/%s.json" % npc)
    ids = {e["id"] for e in entries}
    n["dialogue"] = entries + [d for d in n["dialogue"] if d["id"] not in ids]
    W("npcs/%s.json" % npc, n)

# ---------------------------------------------------------------- objectives
o = L("objectives.json")
o.update({
 "obj_act3_room0": {"text": "Room 0: the Auditor's shelf, at night", "target": {"area": "area_office_auditor", "object": "obj_auditor_shelf"}},
 "obj_act3_back": {"text": "Meet in the Back Room at night", "target": {"area": "area_adjudicator_chamber", "object": "obj_secret_cabinet"}},
 "obj_act4_crake": {"text": "Take the Compact to Lady Crake", "target": {"area": "area_legation_dominion", "object": "obj_crake"}},
 "obj_act4_provost": {"text": "Lay the Compact before the Provost", "target": {"area": "area_office_provost", "object": "obj_provost"}},
 "obj_act4_glut": {"text": "Confront Glut in his Counting-House", "target": {"area": "area_counting_house", "object": "obj_guild_ledger"}},
 "obj_act4_vael": {"text": "Confront Archon Vael at the Legation", "target": {"area": "area_legation_auric", "object": "obj_ashgrove"}},
 "obj_act5_chair": {"text": "Take the Chair", "target": {"area": "area_office_chancellor", "object": "obj_chair"}},
 "obj_free": {"text": "The Border is yours to keep", "target": {"area": "area_office_chancellor", "object": "obj_chair"}}})
W("objectives.json", o)

# ---------------------------------------------------------------- ranks 3-5 privileges
r = L("ranks.json")
priv = {3: [{"icon": "icon_key", "text": "The Upper Cloister's doors open to you"}, {"icon": "icon_quill", "text": "Quotas cross your desk now"},
            {"icon": "icon_obol", "text": "Base pay 16 obols"}],
        4: [{"icon": "icon_key", "text": "The Border Guard answers to you"}, {"icon": "icon_quill", "text": "Envoys must receive you"},
            {"icon": "icon_obol", "text": "Base pay 24 obols"}],
        5: [{"icon": "icon_key", "text": "The Chair is yours"}, {"icon": "icon_quill", "text": "The Principal and the Counterparty will see you"},
            {"icon": "icon_obol", "text": "Base pay 40 obols"}]}
for rk in r["ranks"]:
    if rk["rank"] in priv: rk["privileges"] = priv[rk["rank"]]
W("ranks.json", r)

# ---------------------------------------------------------------- triggers
T = L("triggers.json")
T = [t for t in T if not t["id"].startswith("trg_act")]
T += [
 {"id": "trg_act2_captain", "on": "flag_changed", "match": {"flag_id": "flag_captain_dead"}, "conditions": [], "once": True,
  "effects": [card("The Manifest", "The Captain dissolves into ash. Its ledger is bound in violet, countersigned: C. Thrace, Auditor-General."),
              obj("obj_report_pell")]},
 {"id": "trg_act3_rank", "on": "shift_ended", "match": {}, "once": True,
  "conditions": [F("flag_story_c4"), RANK(2), NOT(RANK(3)), {"op": "stat_gte", "id": "cases_processed", "value": 11}],
  "effects": [card("Department Supervisor", "Marrow's note: 'They are promoting you to keep you busy. Be busier than they expect.'"),
              {"op": "set_rank", "value": 3}, setf("flag_act3"), obj("obj_act3_back")]},
 {"id": "trg_act3_room0", "on": "area_entered", "match": {"area_id": "area_room0"}, "once": False,
  "conditions": [NF("flag_thrace_defeated")],
  "effects": [card("Room 0", "Thrace looks up from a violet ledger. 'You should not be here. Neither should I. Somebody has to be.'"),
              {"op": "spawn_boss", "flag": "flag_thrace_defeated", "kind": "thrace"}]},
 {"id": "trg_act3_thrace", "on": "flag_changed", "match": {"flag_id": "flag_thrace_defeated"}, "once": True, "conditions": [],
  "effects": [card("The Quota Compact", "Room 0's ledger: a Compact fixing souls each way, signed by Archon Vael and Baron Glut."),
              obj("obj_act4_crake")]},
 {"id": "trg_act4_glut", "on": "area_entered", "match": {"area_id": "area_counting_house"}, "once": False,
  "conditions": [RANK(4), NIGHT, NF("flag_glut_defeated")],
  "effects": [card("Quota Night", "Glut, beaming: 'An audit! How thrilling. Let's settle the account the old way.'"),
              {"op": "spawn_boss", "flag": "flag_glut_defeated", "kind": "glut"}]},
 {"id": "trg_act4_glut_down", "on": "flag_changed", "match": {"flag_id": "flag_glut_defeated"}, "once": True, "conditions": [],
  "effects": [card("The Furnace Cools", "Crake seals the Guild's books. 'One signature left, Commissioner. The other half of heaven's choir.'"),
              obj("obj_act4_vael")]},
 {"id": "trg_act4_vael", "on": "area_entered", "match": {"area_id": "area_legation_auric"}, "once": False,
  "conditions": [F("flag_glut_defeated"), NF("flag_vael_defeated")],
  "effects": [card("The Choir", "Vael rises, wings opening. 'You counted wrongly, Commissioner. Let me show you how it is done.'"),
              {"op": "spawn_boss", "flag": "flag_vael_defeated", "kind": "vael"}]},
 {"id": "trg_act4_vael_down", "on": "flag_changed", "match": {"flag_id": "flag_vael_defeated"}, "once": True, "conditions": [],
  "effects": [card("The Chair Offered", "The Compact is broken. By morning the Provost has resigned and the seal on the Chair has been lifted."),
              {"op": "set_rank", "value": 5}, obj("obj_act5_chair")]}]
W("triggers.json", T)

# ---------------------------------------------------------------- Act III: the way into Room 0
lines("dlg_pell_n4", "npc_pell", ["Department Supervisor. They gave you the quotas to keep your hands full. Good. Full hands can carry ledgers.",
    "Odalys kept a copy of Thrace's key. The shelf behind his desk is Room 0's door. It only turns at night, when he's inside.",
    "Go after the night bell. Odalys and Quill will be at your back. Bring me the books."],
    [setf("flag_room0_known"), obj("obj_act3_room0")])
prepend("npc_pell", [{"id": "dlg_pell_n4", "conditions": [NIGHT, RANK(3), F("flag_act3"), NF("flag_room0_known")]}])
W("dialogue/dlg_obj_auditor_shelf.json", {"id": "dlg_obj_auditor_shelf", "start": "n1", "nodes": {
 "n1": {"speaker": "narrator", "text": "The shelf behind the desk, a fraction too deep. Odalys's copied key fits a knot in the wood.",
        "conditions": [NIGHT, F("flag_room0_known"), NF("flag_thrace_defeated")], "next": "ask", "else": "day"},
 "ask": {"speaker": "player", "choices": [{"text": "Turn the key. Go in.", "next": "go"}, {"text": "Not yet.", "next": "end"}]},
 "go": {"speaker": "narrator", "text": "The shelf swings inward on oiled hinges. Violet light. The scratch of a pen that never stops.",
        "effects": [{"op": "teleport", "area": "area_room0", "spawn": "from_office"}], "next": "end"},
 "day": {"speaker": "narrator", "text": "Ledgers, perfectly kept. The shelf behind the desk is a fraction too deep. A draught comes from it.", "next": "end"}}})

# Room 0
g = [list("############")] + [list("#..........k") for _ in range(8)] + [list("kkkkkDkkkkkk")]
for (x, y, ch) in [(2, 1, "g"), (4, 1, "g"), (7, 1, "g"), (9, 1, "g"), (1, 4, "S"), (10, 4, "S"), (5, 3, "e"), (2, 7, "g"), (9, 7, "g")]:
    g[y][x] = ch
area = {"id": "area_room0", "name": "Room 0", "size": [12, 10], "ambience": "amb_hell", "backdrop": "none",
 "grid": ["".join(r) for r in g], "legend": L("areas/area_back_room.json")["legend"] | {"g": {"kind": "prop", "prop": "ledger_stack", "solid": True},
   "e": {"kind": "prop", "prop": "desk_superior", "solid": True}},
 "floor": "floor_flag", "windows": [],
 "decor": [{"sprite": "ink_puddle", "cell": [3, 5]}, {"sprite": "ink_puddle", "cell": [8, 6]}, {"sprite": "light_pool_red", "cell": [5, 5]},
           {"sprite": "rug_red", "cell": [5, 5]}],
 "objects": [{"id": "door_room0_out", "type": "door", "cell": [5, 9], "use_cell": [5, 8], "style": "plain",
              "to": {"area": "area_office_auditor", "spawn": "from_room0"}}],
 "spawns": {"default": [5, 8], "from_office": [5, 8]}, "zones": {},
 "hostiles": {"spawn_cells": [[5, 2]], "boss_cell": [5, 2], "breakout_every": [9999, 9999], "max_enemies": 10,
   "defenders": [{"id": "odalys", "cell": [3, 7], "sprite": "chr_odalys", "night_sprite": "chr_odalys", "hp": 140},
                 {"id": "quill", "cell": [7, 7], "sprite": "chr_guard_night", "night_sprite": "chr_guard_night", "hp": 180, "flag": "flag_quill_ally"}]},
 "ambient": {"desk_clerks": [], "staff": [], "flows": []},
 "ext": {"note": "Act III boss: Auditor-General Corvin Thrace."}}
W("areas/area_room0.json", area)
a = L("areas/area_office_auditor.json"); a["spawns"]["from_room0"] = a["spawns"]["default"]
a["objects"] = [x for x in a["objects"] if x["id"] != "door_auditor_room0"]
a["objects"].append({"id": "door_auditor_room0", "type": "door", "cell": [10, 5], "use_cell": [9, 5], "style": "plain", "secret": True,
    "via": "obj_auditor_shelf", "conditions": [NIGHT, F("flag_room0_known")], "to": {"area": "area_room0", "spawn": "from_office"}})
for x in a["objects"]:
    if x["id"] == "obj_thrace": x["visible_if"] = [NF("flag_thrace_defeated")]
W("areas/area_office_auditor.json", a)

# ---------------------------------------------------------------- Act IV: Crake, the Provost, Glut, Vael
lines("dlg_crake_compact", "npc_crake", ["The Compact. Signed. Glut's paw-print and Vael's perfect hand on the same page.",
    "The Dominion keeps its debts honestly, Supervisor. This is not a debt. This is a sale of the dead.",
    "Take it to the Provost. He will sign anything. Make him sign this. My Wardens will stand with you after."],
    [setf("flag_crake_ally"), obj("obj_act4_provost")])
prepend("npc_crake", [{"id": "dlg_crake_compact", "conditions": [F("flag_thrace_defeated"), NF("flag_crake_ally")]}])
lines("dlg_provost_commission", "npc_provost", ["Oh. Oh dear. Oh dear, oh dear. I signed - I sign everything, you understand -",
    "Very well. Very well! Chief Commissioner of the Border. There. Signed. Read, even. Please don't tell anyone I read it."],
    [{"op": "set_rank", "value": 4}, obj("obj_act4_glut")])
prepend("npc_provost", [{"id": "dlg_provost_commission", "conditions": [F("flag_crake_ally"), RANK(3), NOT(RANK(4))]}])
ch = L("areas/area_counting_house.json")
ch["hostiles"] = {"spawn_cells": [[6, 2]], "boss_cell": [6, 2], "breakout_every": [9999, 9999], "max_enemies": 10,
  "defenders": [{"id": "crake", "cell": [4, 6], "sprite": "chr_crake", "night_sprite": "chr_crake", "hp": 220, "flag": "flag_crake_ally"},
                {"id": "warden", "cell": [8, 6], "sprite": "chr_guard_night", "night_sprite": "chr_guard_night", "hp": 140, "flag": "flag_crake_ally"},
                {"id": "quill", "cell": [6, 7], "sprite": "chr_guard_night", "night_sprite": "chr_guard_night", "hp": 180, "flag": "flag_quill_ally"}]}
for x in ch["objects"]:
    if x["id"] == "obj_glut": x["visible_if"] = [RANK(3), NOT(RANK(4))]
W("areas/area_counting_house.json", ch)
au = L("areas/area_legation_auric.json")
au["hostiles"] = {"spawn_cells": [[8, 2]], "boss_cell": [8, 2], "breakout_every": [9999, 9999], "max_enemies": 10,
  "defenders": [{"id": "ashgrove", "cell": [4, 6], "sprite": "chr_ashgrove", "night_sprite": "chr_ashgrove", "hp": 160, "flag": "flag_glut_defeated"},
                {"id": "warden", "cell": [8, 6], "sprite": "chr_guard", "night_sprite": "chr_guard_night", "hp": 140, "flag": "flag_crake_ally"}]}
for x in au["objects"]:
    if x["id"] == "obj_vael": x["visible_if"] = [RANK(3), NF("flag_glut_defeated")]
W("areas/area_legation_auric.json", au)

# ---------------------------------------------------------------- Act V: the Chair and the three endings
W("dialogue/dlg_obj_chair.json", {"id": "dlg_obj_chair", "start": "n1", "nodes": {
 "n1": {"speaker": "narrator", "text": "The Chair. On the seat, a single file. Your name is on it.", "conditions": [RANK(5)], "next": "sit", "else": "nope"},
 "nope": {"speaker": "narrator", "text": "The Chair. Black wood, gold leaf, worn at the arms by hands that have not touched it in decades.", "next": "end"},
 "sit": {"speaker": "narrator", "text": "You sit. The room goes quiet in two directions at once. Two presences arrive, and do not knock.",
         "conditions": [NF("flag_ending_chosen")], "next": "p1", "else": "after"},
 "p1": {"speaker": "narrator", "text": "The Principal: 'You broke a Compact that kept a peace. Tell Us what you will keep instead.'", "next": "c1"},
 "c1": {"speaker": "narrator", "text": "The Counterparty, amused: 'Choose carefully, Chancellor. We both remember the Tally War.'", "next": "choose"},
 "choose": {"speaker": "player", "choices": [
   {"text": "Keep the Rubric. Order, honestly kept.", "next": "e1", "effects": [setf("flag_ending_rubric"), setf("flag_ending_chosen")]},
   {"text": "Restore discretion. Judge every soul.", "next": "e2", "effects": [setf("flag_ending_discretion"), setf("flag_ending_chosen")]},
   {"text": "Charter Purgatory as a third realm.", "next": "e3", "effects": [setf("flag_ending_charter"), setf("flag_ending_chosen")]}]},
 "e1": {"speaker": "narrator", "text": "The Rubric stands, without violet ink. Fewer miracles, fewer crimes. The queue moves. The Gates stay shut to bribes.",
        "effects": [card("The Rubric Kept", "Order, honestly kept. The Border endures. (The work goes on; so can you.)"), obj("obj_free")], "next": "end"},
 "e2": {"speaker": "narrator", "text": "Every file is judged by a person again. It is slower, kinder, and dangerous. Both sides grumble. Neither marches.",
        "effects": [card("Discretion Restored", "Justice, one soul at a time. The backlog grows; so does mercy. (Play on.)"), obj("obj_free")], "next": "end"},
 "e3": {"speaker": "narrator", "text": "The DEFERRED are no longer waiting. Purgatory is a realm, with its own name. The Residents weep in the Cells, then open them.",
        "effects": [card("The Third Realm", "Purgatory chartered. Nobody is merely deferred any more. (Play on.)"), obj("obj_free")], "next": "end"},
 "after": {"speaker": "narrator", "text": "The Chair is warm now. The file with your name on it waits. You will open it one day. Not today.", "next": "end"}}})
print("acts written")
