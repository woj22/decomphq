extends Node
## Loads all content JSON at boot (04 §4.1). Read-only lookups.
## Each data sub-path falls back to res://tests/fixtures/data/ when missing in res://data/.

const DATA_ROOT := "res://data"
const FIXTURE_ROOT := "res://tests/fixtures/data"

## Engine defaults for every number the engine needs (PROJECT §2, §6, §10.6). config.json overrides.
const DEFAULTS := {
	"composure": 3,
	"player_speed": 3.0,
	"interaction_radius": 1.5,
	"clock_start": 480,
	"overtime_after": 1080,
	"clock_costs": {"door": 5, "question_general": 10, "question_confront": 5, "archive": 15, "verdict": 20, "link": 0},
	"queue_arrival_start": 16,
	"queue_bench_start": 8,
	"queue_bench_cap": 12,
	"arrival_rate_early": 3.0,
	"arrival_rate_late": 2.0,
	"arrival_rate_switch": 600,
	"registrar_rate": 2.4,
	"adjudicator_rate": 1.2,
	"adjudicator_hell_share": 0.6,
	"order_start": 68,
	"order_queue_free": 30,
	"purse_start": 12,
	"pay_base": 8,
	"pay_accuracy_bonus": 3,
	"pay_accuracy_threshold": 0.8,
	"lamp_price": 20,
	"merit_gate": 30,
	"overturned_max": 2,
	"sim_seed": 991,
	"dockets": {},
}

var root_used := {}
var config: Dictionary = {}
var ranks: Dictionary = {}
var triggers: Array = []
var objectives: Dictionary = {}
var _areas := {}
var _npcs := {}
var _dialogues := {}
var _cases := {}
var errors: PackedStringArray = []
var _forced_root := ""


func _ready() -> void:
	for a: String in OS.get_cmdline_user_args() + OS.get_cmdline_args():
		if a.begins_with("--data="):
			_forced_root = a.substr(7)
	reload()


func _root_for(sub: String) -> String:
	if _forced_root != "":
		return _forced_root
	var p := DATA_ROOT.path_join(sub)
	if DirAccess.dir_exists_absolute(p) or FileAccess.file_exists(p):
		return DATA_ROOT
	return FIXTURE_ROOT


func reload(force_root: String = "") -> void:
	if force_root != "":
		_forced_root = force_root
	errors = []
	root_used = {}
	_areas = _load_dir("areas")
	_npcs = _load_dir("npcs")
	_dialogues = _load_dir("dialogue")
	_cases = _load_dir("cases")
	config = _load_one("config.json", {}) as Dictionary
	ranks = _load_one("ranks.json", {}) as Dictionary
	var t: Variant = _load_one("triggers.json", [])
	if t is Dictionary and (t as Dictionary).has("triggers"):
		t = (t as Dictionary)["triggers"]
	triggers = t if t is Array else []
	var o: Variant = _load_one("objectives.json", {})
	if o is Dictionary and (o as Dictionary).has("objectives") and (o as Dictionary)["objectives"] is Dictionary:
		o = (o as Dictionary)["objectives"]
	objectives = o if o is Dictionary else {}
	print("[Content] areas=%d npcs=%d dialogue=%d cases=%d triggers=%d roots=%s" % [_areas.size(), _npcs.size(),
		_dialogues.size(), _cases.size(), triggers.size(), str(root_used)])


func _load_dir(sub: String) -> Dictionary:
	var root := _root_for(sub)
	root_used[sub] = root
	var out := {}
	for f: String in JsonUtil.list_files(root.path_join(sub), ".json"):
		var d: Variant = JsonUtil.load_file(f)
		if d is Dictionary:
			var dd: Dictionary = d
			var id := str(dd.get("id", f.get_file().get_basename()))
			out[id] = dd
		else:
			errors.append("bad json " + f)
	return out


func _load_one(file: String, fallback: Variant) -> Variant:
	var root := _root_for(file)
	root_used[file] = root
	var p := root.path_join(file)
	if not FileAccess.file_exists(p):
		return fallback
	var d: Variant = JsonUtil.load_file(p)
	if d == null:
		errors.append("bad json " + p)
		return fallback
	return d


func using_fixtures() -> bool:
	for k: String in root_used:
		if root_used[k] == FIXTURE_ROOT:
			return true
	return false


func area(id: String) -> Dictionary:
	return _areas.get(id, {})


func npc(id: String) -> Dictionary:
	return _npcs.get(id, {})


func dialogue(id: String) -> Dictionary:
	return _dialogues.get(id, {})


func case(id: String) -> Dictionary:
	return _cases.get(id, {})


func area_ids() -> Array:
	var a := _areas.keys()
	a.sort()
	return a


func case_ids() -> Array:
	var a := _cases.keys()
	a.sort()
	return a


func npc_ids() -> Array:
	return _npcs.keys()


func dialogue_ids() -> Array:
	return _dialogues.keys()


func objective(id: String) -> Dictionary:
	var o: Variant = objectives.get(id, {})
	if o is String:
		return {"text": o}
	return o if o is Dictionary else {}


## Engine key -> paths tried in config.json (Content's layout first).
const ALIASES := {
	"composure": ["judgement.composure"],
	"player_speed": ["player.speed_cells_per_s", "player.speed"],
	"interaction_radius": ["player.interaction_radius_cells"],
	"clock_start": ["clock.day_start_minutes", "start.minutes"],
	"overtime_after": ["clock.overtime_from_minutes"],
	"queue_arrival_start": ["queue.arrival_start"],
	"queue_bench_start": ["queue.bench_start"],
	"queue_bench_cap": ["queue.bench_cap"],
	"arrival_rate_early": ["queue.arrival_rate_per_h_before"],
	"arrival_rate_late": ["queue.arrival_rate_per_h_after"],
	"arrival_rate_switch": ["queue.arrival_rate_switch_minutes"],
	"registrar_rate": ["queue.registrar_rate_per_h"],
	"adjudicator_rate": ["queue.adjudicator_rate_per_h_total"],
	"adjudicator_hell_share": ["queue.npc_hell_share"],
	"order_start": ["order.start"],
	"order_queue_free": ["order.queue_threshold"],
	"purse_start": ["pay.purse_start"],
	"pay_accuracy_bonus": ["pay.accuracy_bonus"],
	"pay_accuracy_threshold": ["pay.accuracy_threshold"],
	"lamp_price": ["items.item_desk_lamp.price"],
	"merit_gate": ["promotion.merit_min"],
	"overturned_max": ["promotion.overturned_max"],
	"sim_seed": ["seed"],
}


## Config lookup with engine defaults. Accepts dotted paths ("clock_costs.door") and a few aliases.
func cfg(key: String, fallback: Variant = null) -> Variant:
	var v: Variant = _lookup(config, key)
	if v != null:
		return v
	for alt: String in ALIASES.get(key, []):
		v = _lookup(config, alt)
		if v != null:
			return v
	v = _lookup(DEFAULTS, key)
	if v != null:
		return v
	return fallback


func cfg_i(key: String, fallback: int = 0) -> int:
	var v: Variant = cfg(key, fallback)
	return int(v) if (v is int or v is float) else fallback


func cfg_f(key: String, fallback: float = 0.0) -> float:
	var v: Variant = cfg(key, fallback)
	return float(v) if (v is int or v is float) else fallback


func _lookup(d: Dictionary, key: String) -> Variant:
	if d.has(key):
		return d[key]
	var cur: Variant = d
	for part in key.split("."):
		if cur is Dictionary and (cur as Dictionary).has(part):
			cur = (cur as Dictionary)[part]
		else:
			return null
	return cur


## Clock cost for an action reason (door, question_general, question_confront, archive, verdict).
func clock_cost(reason: String) -> int:
	var aliases := {"door": ["door", "area_transition", "transition"], "question_general": ["question_general", "general_question", "question"],
		"question_confront": ["question_confront", "confront_question", "confrontation"], "archive": ["archive", "archive_request"],
		"verdict": ["verdict", "stamp"]}
	for src: String in ["clock_costs", "clock.costs", "clock", "clock_minutes", "costs"]:
		var c: Variant = _lookup(config, src)
		if c is Dictionary:
			for k: String in aliases.get(reason, [reason]):
				if (c as Dictionary).has(k) and ((c as Dictionary)[k] is int or (c as Dictionary)[k] is float):
					return int((c as Dictionary)[k])
	return int((DEFAULTS["clock_costs"] as Dictionary).get(reason, 0))


func docket(day: int) -> Array:
	var d: Variant = cfg("dockets", {})
	if d is Dictionary:
		var v: Variant = (d as Dictionary).get(str(day), [])
		return v if v is Array else []
	return []


func rank_info(n: int) -> Dictionary:
	var arr: Variant = ranks.get("ranks", [])
	if arr is Array:
		for r: Dictionary in arr:
			if int(r.get("rank", 0)) == n:
				return r
	return {}


func max_rank() -> int:
	var m := 1
	var arr: Variant = ranks.get("ranks", [])
	if arr is Array:
		for r: Dictionary in arr:
			m = maxi(m, int(r.get("rank", 1)))
	return m


func rank_title(n: int) -> String:
	var r := rank_info(n)
	if r.has("title"):
		return str(r["title"])
	return ["", "Junior Processing Clerk", "Senior Adjudicator", "Department Supervisor", "Chief Commissioner", "High Chancellor"][clampi(n, 0, 5)]


## Stat definitions: [{id, name, start, min?, max?}]
func stat_defs() -> Array:
	var s: Variant = ranks.get("stats", [])
	return s if s is Array else []
