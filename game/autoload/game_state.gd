extends Node
## All mutable, saveable state (04 §4.1). Conditions/effects read and write here.

const DEFAULT_STATS := {"merit": 0, "order": 68, "purse": 12, "queue": 24, "overturned": 0, "cases_processed": 0,
	"favour_gilt": 0, "favour_ember": 0, "conscience": 0, "sound": 0, "unsound": 0, "resolved": 0, "unresolved": 0, "order_adj": 0}
const RESTORABLE := ["merit", "overturned", "cases_processed", "sound", "unsound", "favour_gilt", "favour_ember", "conscience"]

var rank := 1
var stats: Dictionary = {}
var flags: Dictionary = {}
var cases: Dictionary = {}
var docket: Array = []
var docket_day := 0
var objective := ""
var unlocked_areas: Array = []
var incidents: Dictionary = {}
var items: Dictionary = {}
var snapshots: Dictionary = {}
var shift: Dictionary = {}
var pending_scored: Array = []
var triggers_fired: Dictionary = {}
var dialogue_log: Array = []
var back_room_log: Array = [] # lines spoken in the Back Room (the companion was present)
var last_ledger: Dictionary = {}
var choices_log: Array = []
var in_game := false
var triggers := TriggerRunner.new()


func _ready() -> void:
	triggers.connect_bus()
	EventBus.line_shown.connect(_on_line)
	reset()


func reset() -> void:
	rank = 1
	stats = {}
	for k: String in DEFAULT_STATS:
		stats[k] = DEFAULT_STATS[k]
	stats["order"] = Content.cfg_i("order_start", 68)
	stats["purse"] = Content.cfg_i("purse_start", 12)
	for s: Variant in Content.stat_defs():
		if s is Dictionary and (s as Dictionary).has("id"):
			_store(str(s["id"]), float((s as Dictionary).get("start", 0)))
	flags = {}
	cases = {}
	docket = []
	docket_day = 0
	objective = ""
	unlocked_areas = []
	incidents = {}
	items = {}
	snapshots = {}
	shift = _blank_shift()
	pending_scored = []
	triggers_fired = {}
	dialogue_log = []
	back_room_log = []
	last_ledger = {}
	choices_log = []


func _blank_shift() -> Dictionary:
	return {"processed": 0, "sound": 0, "unsound": 0, "heaven": 0, "hell": 0, "overturned": 0, "key_found": 0, "key_total": 0,
		"merit": 0, "cases": []}


func new_game() -> void:
	reset()
	Clock.reset()
	Sim.reset()
	recompute_derived()
	in_game = true
	EventBus.new_game_started.emit()


# ---------------------------------------------------------------- flags & stats
func get_flag(id: String) -> Variant:
	return flags.get(id, false)


func flag_true(id: String) -> bool:
	var v: Variant = flags.get(id, false)
	if v == null:
		return false
	if v is bool:
		return v
	if v is String:
		return v != "" and v != "false"
	if v is int or v is float:
		return float(v) != 0.0
	return true


func set_flag(id: String, value: Variant = true) -> void:
	if id == "":
		return
	flags[id] = value
	EventBus.flag_changed.emit(id, value)


func get_stat(id: String) -> float:
	return float(stats.get(id, 0))


func get_stat_i(id: String) -> int:
	return int(round(get_stat(id)))


func add_stat(id: String, delta: float) -> void:
	if id == "order":
		id = "order_adj"
	var cur := get_stat(id)
	_store(id, cur + delta)
	EventBus.stat_changed.emit(id, stats[id], delta)
	recompute_derived()


func set_stat(id: String, value: float) -> void:
	var cur := get_stat(id)
	_store(id, value)
	EventBus.stat_changed.emit(id, stats[id], value - cur)
	recompute_derived()


func _store(id: String, v: float) -> void:
	if is_equal_approx(v, round(v)):
		stats[id] = int(round(v))
	else:
		stats[id] = v


## Queue and Order are derived (PROJECT §6).
func recompute_derived() -> void:
	var q := Sim.queue_total()
	var old_q := get_stat_i("queue")
	stats["queue"] = q
	var o := Scoring.order_value(Content.cfg_i("order_start", 68), get_stat_i("sound"), get_stat_i("unsound"), q,
		get_stat_i("resolved"), get_stat_i("unresolved"), Content.cfg_i("order_queue_free", 30), get_stat_i("order_adj"))
	var old_o := get_stat_i("order")
	stats["order"] = o
	if old_q != q:
		EventBus.stat_changed.emit("queue", q, q - old_q)
	if old_o != o:
		EventBus.stat_changed.emit("order", o, o - old_o)


func set_objective(id: String) -> void:
	objective = id
	EventBus.objective_changed.emit(id)


func objective_text() -> String:
	if objective == "":
		return ""
	var o := Content.objective(objective)
	return str(o.get("text", objective))


# ---------------------------------------------------------------- cases
func case_rec(cid: String, create: bool = true) -> Dictionary:
	if not cases.has(cid):
		if not create:
			return {}
		cases[cid] = {"state": "pending", "composure": Content.cfg_i("composure", 3), "asked": [], "links": [], "discoveries": [],
			"archive": [], "ground": "", "verdict": "", "merit": 0, "sound": false, "result": {}, "correction": false,
			"answers": {}, "day": 0}
	return cases[cid]


func case_state(cid: String) -> String:
	if cid == "" or not cases.has(cid):
		return "pending"
	return str((cases[cid] as Dictionary).get("state", "pending"))


func case_verdict(cid: String) -> String:
	if not cases.has(cid):
		return ""
	return str((cases[cid] as Dictionary).get("verdict", ""))


func is_discovered(cid: String, did: String) -> bool:
	return cases.has(cid) and ((cases[cid] as Dictionary).get("discoveries", []) as Array).has(did)


func is_asked(cid: String, qid: String) -> bool:
	return cases.has(cid) and ((cases[cid] as Dictionary).get("asked", []) as Array).has(qid)


func holds_archive(cid: String, aid: String) -> bool:
	return cases.has(cid) and ((cases[cid] as Dictionary).get("archive", []) as Array).has(aid)


func archive_available(cid: String) -> bool:
	if cid == "":
		return false
	return not JudgementSession.new(cid).available_archive().is_empty()


func active_case_id() -> String:
	# The case currently with the player: called (following) or seated.
	for cid: Variant in docket:
		var s := case_state(str(cid))
		if s == "called" or s == "seated":
			return str(cid)
	for cid: String in cases:
		var s := case_state(cid)
		if s == "called" or s == "seated":
			return cid
	return ""


func docket_empty() -> bool:
	for cid: Variant in docket:
		if case_state(str(cid)) != "judged":
			return false
	return true


func docket_remaining() -> Array:
	var out: Array = []
	for cid: Variant in docket:
		if case_state(str(cid)) != "judged":
			out.append(str(cid))
	return out


func give_docket(day: int) -> void:
	docket = Content.docket(day).duplicate()
	docket_day = day
	for cid: Variant in docket:
		case_rec(str(cid))
	EventBus.docket_changed.emit()


func start_shift(day: int) -> void:
	Clock.start_shift(day)
	shift = _blank_shift()
	EventBus.shift_started.emit(day)


func end_shift() -> void:
	var summary := shift_summary()
	var pay: int = summary["pay"]
	add_stat("purse", pay)
	Clock.stop_shift()
	last_ledger = summary
	Dialogue.request_modal("ledger", summary)


func shift_summary() -> Dictionary:
	var processed: int = shift["processed"]
	var pay := Scoring.pay_value(pay_base(), processed, shift["sound"], shift["unsound"], Content.cfg_i("pay_accuracy_bonus", 3),
		Content.cfg_f("pay_accuracy_threshold", 0.8))
	return {"day": Clock.day, "processed": processed, "heaven": shift["heaven"], "hell": shift["hell"], "sound": shift["sound"],
		"unsound": shift["unsound"], "overturned": shift["overturned"], "key_found": shift["key_found"], "key_total": shift["key_total"],
		"pay": pay, "purse_after": get_stat_i("purse") + pay, "order": get_stat_i("order"), "merit": get_stat_i("merit"),
		"merit_gate": Content.cfg_i("merit_gate", 30), "overturned_total": get_stat_i("overturned")}


func pay_base() -> int:
	var r := Content.rank_info(rank)
	for k: String in ["base_pay", "pay_base"]:
		if r.has(k):
			return int(r[k])
	var by_rank: Variant = Content.cfg("pay_base_by_rank")
	if by_rank is Dictionary and (by_rank as Dictionary).has(str(rank)):
		return int((by_rank as Dictionary)[str(rank)])
	if rank >= 2:
		return Content.cfg_i("pay_base_r2", 12)
	return Content.cfg_i("pay_base", 8)


func sign_ledger() -> void:
	var s := last_ledger
	EventBus.shift_ended.emit(int(s.get("day", Clock.day)), s)
	SaveGame.autosave("shift_sign")


func call_soul(cid: String = "") -> String:
	if active_case_id() != "":
		EventBus.notify.emit("A soul is already with you.")
		return ""
	var target := cid
	if target == "":
		for c: Variant in docket:
			if case_state(str(c)) == "pending":
				target = str(c)
				break
	if target == "":
		EventBus.notify.emit("Your docket is empty.")
		return ""
	var rec := case_rec(target)
	rec["state"] = "called"
	rec["day"] = Clock.day
	Sim.take_arrival()
	recompute_derived()
	EventBus.case_called.emit(target)
	EventBus.docket_changed.emit()
	return target


func seat_case(cid: String) -> void:
	var rec := case_rec(cid)
	if rec["state"] == "called":
		rec["state"] = "seated"
		EventBus.case_seated.emit(cid)


func give_archive(cid: String) -> Array:
	if cid == "":
		return []
	return JudgementSession.new(cid).request_archive()


func give_archive_one(cid: String, aid: String) -> void:
	if cid == "" or aid == "":
		return
	JudgementSession.new(cid).receive_archive([aid])


func reopen_case(cid: String) -> void:
	if cid == "" or not cases.has(cid):
		return
	var rec: Dictionary = cases[cid]
	if rec["state"] != "judged":
		return
	var res: Dictionary = rec.get("result", {})
	add_stat("merit", -int(res.get("merit", 0)))
	add_stat("cases_processed", -1)
	if str(rec.get("verdict", "")) == "hell" and get_stat_i("escort_pending") > 0:
		add_stat("escort_pending", -1)
	if bool(res.get("deferred", false)):
		add_stat("deferred", -1)
	elif bool(res.get("sound", false)):
		add_stat("sound", -1)
	else:
		add_stat("unsound", -1)
	if bool(res.get("overturned", false)):
		add_stat("overturned", -1)
	var applied: Dictionary = res.get("hidden_applied", {})
	for k: String in applied:
		add_stat(k, -int(applied[k]))
	# revert the hidden stats the verdict effects added (favour/conscience)
	var vd: Variant = Content.case(cid).get("verdicts", {})
	if vd is Dictionary and (vd as Dictionary).get(str(rec.get("verdict", ""))) is Dictionary:
		for e: Variant in ((vd as Dictionary)[str(rec["verdict"])] as Dictionary).get("effects", []):
			if e is Dictionary and str((e as Dictionary).get("op", "")) == "add_stat":
				var sid := str((e as Dictionary).get("id", ""))
				if sid in ["favour_gilt", "favour_ember", "conscience"]:
					add_stat(sid, -float((e as Dictionary).get("value", 0)))
	rec["state"] = "seated"
	rec["correction"] = true
	rec["verdict"] = ""
	rec["ground"] = ""
	rec["result"] = {}
	if not docket.has(cid):
		docket.append(cid)
	EventBus.docket_changed.emit()


## Rank 2+: a judged case comes back on appeal. Its earlier score is reverted (re-scored on the new stamp), the investigation
## so far is kept, Composure is restored, and the soul waits to be called again. `by` = "soul" | "gilt" | "ember".
func appeal_case(cid: String, by: String = "soul") -> void:
	if cid == "" or case_state(cid) != "judged":
		return
	var prev := case_verdict(cid)
	reopen_case(cid)
	var rec := case_rec(cid)
	rec["state"] = "pending"
	rec["correction"] = false
	rec["appeal"] = {"from": prev, "by": by}
	rec["composure"] = Content.cfg_i("composure", 3)
	if not docket.has(cid):
		docket.append(cid)
	EventBus.docket_changed.emit()


## Souls the player stamped DEFERRED: they stay in the fortress as Residents (shown wandering Clerk's Court).
func residents() -> Array:
	var out: Array = []
	for cid: String in cases:
		if case_state(cid) == "judged" and case_verdict(cid) == "purgatory":
			out.append(cid)
	return out


## Rank 2+ endless work: three generated souls and one appeal of an earlier verdict, then a shift begins.
func next_docket() -> void:
	if not docket_empty():
		EventBus.notify.emit("Finish today's docket first.")
		return
	var seed_v: Variant = flags.get("world_seed")
	if seed_v == null:
		seed_v = randi() % 1000000
		flags["world_seed"] = seed_v
	var dd := maxi(docket_day + 1, 4)
	var ids: Array = []
	for i in Content.cfg_i("gen_docket_size", 3):
		add_stat("gen_serial", 1)
		ids.append("gen_%d_%d" % [int(seed_v), get_stat_i("gen_serial")])
	docket = ids
	docket_day = dd
	for cid: Variant in ids:
		case_rec(str(cid))
	# a soul you trapped in the Deferral Cells comes up for a final decision
	var res := residents()
	if not res.is_empty():
		appeal_case(str(res[randi() % res.size()]), "cells")
	# an earlier verdict comes back on appeal
	var judged: Array = []
	for cid: String in cases:
		if case_state(cid) == "judged" and not (case_rec(cid) as Dictionary).has("appeal") and case_verdict(cid) in ["heaven", "hell"]:
			judged.append(cid)
	if not judged.is_empty():
		var a: String = judged[randi() % judged.size()]
		appeal_case(a, "soul" if case_verdict(a) == "hell" else "ember")
	set_flag("flag_gen_shift", true)
	start_shift(dd)
	EventBus.docket_changed.emit()


func snapshot_stats(tag: String) -> void:
	snapshots[tag] = {"stats": stats.duplicate(true), "rank": rank}


func restore_stats(tag: String) -> void:
	if not snapshots.has(tag):
		return
	var snap: Dictionary = (snapshots[tag] as Dictionary).get("stats", {})
	for k: String in snap:
		if k != "queue" and k != "order":
			stats[k] = snap[k]
	recompute_derived()
	for k: String in snap:
		EventBus.stat_changed.emit(k, stats.get(k, 0), 0)


func reset_cases(ids: Array) -> void:
	for cid: Variant in ids:
		cases.erase(str(cid))
		case_rec(str(cid))
		pending_scored.erase(str(cid))
	EventBus.docket_changed.emit()


func set_incident(id: String, state: String) -> void:
	var prev := str(incidents.get(id, ""))
	if prev == state:
		return
	if prev == "resolved" or prev == "unresolved":
		return # an incident is decided once
	incidents[id] = state
	if state == "resolved":
		add_stat("resolved", 1)
	elif state == "unresolved":
		add_stat("unresolved", 1)
	EventBus.incident_changed.emit(id, state)


func unlock_area(id: String) -> void:
	if not unlocked_areas.has(id):
		unlocked_areas.append(id)
		EventBus.area_unlocked.emit(id)


func set_rank(value: int) -> void:
	var old := rank
	rank = value
	if value > old:
		Dialogue.request_modal("ceremony", {"from": old, "to": value})
	EventBus.rank_changed.emit(value)


func buy_item(id: String, price: int) -> bool:
	if items.has(id):
		EventBus.notify.emit("You already have that.")
		return false
	if get_stat_i("purse") < price:
		EventBus.notify.emit("Not enough obols.")
		return false
	add_stat("purse", -price)
	items[id] = true
	set_flag("has_" + id, true)
	EventBus.item_bought.emit(id)
	return true


## Records a stamped verdict (called by JudgementSession).
func record_verdict(cid: String, result: Dictionary) -> void:
	var rec := case_rec(cid)
	rec["state"] = "judged"
	rec["verdict"] = result["verdict"]
	rec["ground"] = result["ground"]
	rec["merit"] = result["merit"]
	rec["sound"] = result["sound"]
	rec["result"] = result
	add_stat("merit", int(result["merit"]))
	add_stat("cases_processed", 1)
	if str(result["verdict"]) == "hell":
		add_stat("escort_pending", 1)
	if bool(result.get("deferred", false)):
		add_stat("deferred", 1)
	else:
		add_stat("sound" if result["sound"] else "unsound", 1)
	if result["overturned"]:
		add_stat("overturned", 1)
	# Hidden favour/conscience are applied by the case's verdict effects (CONTRACT_CHANGES #4), never here.
	result["hidden_applied"] = {}
	shift["processed"] = int(shift["processed"]) + 1
	if not bool(result.get("deferred", false)):
		shift["sound" if result["sound"] else "unsound"] = int(shift["sound" if result["sound"] else "unsound"]) + 1
	shift[result["verdict"]] = int(shift.get(result["verdict"], 0)) + 1
	if result["overturned"]:
		shift["overturned"] = int(shift["overturned"]) + 1
	shift["key_found"] = int(shift["key_found"]) + int(result["key_found"])
	shift["key_total"] = int(shift["key_total"]) + int(result["key_total"])
	shift["merit"] = int(shift["merit"]) + int(result["merit"])
	(shift["cases"] as Array).append(cid)
	if not pending_scored.has(cid):
		pending_scored.append(cid)
	EventBus.case_judged.emit(cid, str(result["verdict"]))


## Emits case_scored for a stamped case once its presentation finished (audit slip dismissed).
func finish_case(cid: String) -> void:
	if not pending_scored.has(cid):
		return
	pending_scored.erase(cid)
	var res: Dictionary = (cases.get(cid, {}) as Dictionary).get("result", {})
	EventBus.case_scored.emit(cid, res)


func flush_pending_scored() -> void:
	for cid: Variant in pending_scored.duplicate():
		finish_case(str(cid))


## Engine-side evaluation of the rank 1 -> 2 gate (PROJECT §4). Content triggers drive the actual flow.
func gate_result() -> String:
	if get_stat_i("cases_processed") < 6:
		return "incomplete"
	if not flag_true("flag_found_violet_ink"):
		return "correction"
	if get_stat_i("merit") < Content.cfg_i("merit_gate", 30) or get_stat_i("overturned") > Content.cfg_i("overturned_max", 2):
		return "reissue"
	return "pass"


func _on_line(speaker: String, text: String) -> void:
	dialogue_log.append({"speaker": speaker, "text": text})
	if World.area_id == "area_back_room":
		var nm := speaker
		var n := Content.npc(speaker)
		if not n.is_empty():
			nm = str(n.get("name", speaker))
		back_room_log.append({"speaker": nm, "text": text})
		while back_room_log.size() > 30:
			back_room_log.pop_front()
	while dialogue_log.size() > 20:
		dialogue_log.pop_front()


# ---------------------------------------------------------------- save/restore
func to_dict() -> Dictionary:
	return {"rank": rank, "stats": stats.duplicate(true), "flags": flags.duplicate(true), "cases": cases.duplicate(true),
		"docket": docket.duplicate(), "docket_day": docket_day, "objective": objective, "unlocked_areas": unlocked_areas.duplicate(),
		"incidents": incidents.duplicate(), "items": items.duplicate(), "snapshots": snapshots.duplicate(true),
		"shift": shift.duplicate(true), "pending_scored": pending_scored.duplicate(), "triggers_fired": triggers_fired.duplicate(),
		"dialogue_log": dialogue_log.duplicate(true), "back_room_log": back_room_log.duplicate(true), "last_ledger": last_ledger.duplicate(true), "choices_log": choices_log.duplicate(true)}


## JSON turns ints into floats; restore integral values to int, recursively.
static func normalize(v: Variant) -> Variant:
	if v is float and is_equal_approx(v, round(v)) and absf(v) < 1.0e12:
		return int(round(v))
	if v is Dictionary:
		var out := {}
		for k: Variant in v:
			out[k] = normalize((v as Dictionary)[k])
		return out
	if v is Array:
		var a: Array = []
		for x: Variant in v:
			a.append(normalize(x))
		return a
	return v


func from_dict(raw: Dictionary) -> void:
	var d: Dictionary = normalize(raw)
	reset()
	rank = int(d.get("rank", 1))
	stats = (d.get("stats", stats) as Dictionary).duplicate(true)
	for k: String in DEFAULT_STATS:
		if not stats.has(k):
			stats[k] = DEFAULT_STATS[k]
	# JSON numbers come back as floats; normalise integral values.
	for k: String in stats.keys():
		_store(k, float(stats[k]))
	flags = (d.get("flags", {}) as Dictionary).duplicate(true)
	cases = (d.get("cases", {}) as Dictionary).duplicate(true)
	for cid: String in cases:
		var rec: Dictionary = cases[cid]
		rec["composure"] = int(rec.get("composure", 3))
		rec["merit"] = int(rec.get("merit", 0))
	docket = (d.get("docket", []) as Array).duplicate()
	docket_day = int(d.get("docket_day", 0))
	objective = str(d.get("objective", ""))
	unlocked_areas = (d.get("unlocked_areas", []) as Array).duplicate()
	incidents = (d.get("incidents", {}) as Dictionary).duplicate()
	items = (d.get("items", {}) as Dictionary).duplicate()
	snapshots = (d.get("snapshots", {}) as Dictionary).duplicate(true)
	shift = (d.get("shift", _blank_shift()) as Dictionary).duplicate(true)
	for k: String in shift.keys():
		if shift[k] is float:
			shift[k] = int(shift[k])
	pending_scored = (d.get("pending_scored", []) as Array).duplicate()
	triggers_fired = (d.get("triggers_fired", {}) as Dictionary).duplicate()
	dialogue_log = (d.get("dialogue_log", []) as Array).duplicate(true)
	back_room_log = (d.get("back_room_log", []) as Array).duplicate(true)
	last_ledger = (d.get("last_ledger", {}) as Dictionary).duplicate(true)
	choices_log = (d.get("choices_log", []) as Array).duplicate(true)
	in_game = true
