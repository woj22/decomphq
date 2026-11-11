class_name AmbientLife
extends Node
## Real-time ambient population for an area: wandering staff, desk clerks at every unclaimed desk, and souls that
## flow through the fortress on their own (arrive, cross, get judged at a desk, leave by the Gilt or Ember door).
## Presentation only: never touches Sim counters, GameState, the clock or saves, so scoring and tests are unaffected.
##
## Area JSON (optional) `"ambient"`:
##   "staff":  [{"sprite": "chr_clerk_grey", "count": 2, "rect": [x0, y0, x1, y1]?, "pause": [min, max]?}]
##   "flows":  [{"kind": "pass",   "from": [[x, y], ...], "to": [[x, y], ...], "every": [min, max]}
##              {"kind": "judged", "from": [[x, y], ...], "every": [min, max], "hell_share": 0.6}]
##   "desk_clerks": ["chr_clerk_grey", "chr_clerk_lilac"]   (sprites cycled over auto-detected desks; [] disables)
##   "max_walkers": 14
## Desks: every `desk_clerk` prop not claimed by an object gets a working clerk on the cell behind it (y - 1) and a
## soul seat in front of it (y + 1), when those cells are open.

const FADE_S := 0.6

var model: AreaModel
var container: Node2D
var rng := RandomNumberGenerator.new()
var cfg: Dictionary = {}
var desks: Array = [] # [{clerk: Vector2i, seat: Vector2i, busy: bool, actor: Actor}]
var walkers: Array = [] # live soul walkers
var _flow_t: Array = [] # countdown per flow
var _max_walkers := 14


func setup(m: AreaModel, parent: Node2D) -> void:
	model = m
	container = parent
	rng.randomize()
	var a: Variant = m.data.get("ambient", {})
	cfg = a if a is Dictionary else {}
	_max_walkers = int(cfg.get("max_walkers", 14))
	_build_desks()
	_build_staff()
	_build_residents()
	for f: Variant in cfg.get("flows", []):
		_flow_t.append(rng.randf_range(0.3, 2.0))
	# Pre-warm: a couple of souls already mid-journey so a room never opens empty.
	for i in 2:
		for fi in _flow_t.size():
			_spawn_flow(fi, true)


# ---------------------------------------------------------------- desks
func _claimed_desks() -> Dictionary:
	var claimed := {}
	for o: Variant in model.objects:
		if not (o is Dictionary):
			continue
		var od: Dictionary = o
		if od.has("desk"):
			claimed[JsonUtil.to_vec2i(od["desk"])] = true
		if str(od.get("type", "")) == "desk_player":
			claimed[JsonUtil.to_vec2i(od.get("cell"))] = true
	return claimed


func _build_desks() -> void:
	var sprites: Array = cfg.get("desk_clerks", ["chr_clerk_grey", "chr_clerk_lilac", "chr_clerk_grey"])
	if sprites.is_empty() or (Clock.is_night() and not bool(cfg.get("desks_at_night", false))):
		return
	var claimed := _claimed_desks()
	var n := 0
	for y in model.size.y:
		for x in model.size.x:
			var c := Vector2i(x, y)
			if claimed.has(c) or str(model.def_at(c).get("prop", "")) != "desk_clerk":
				continue
			var clerk := c + Vector2i(0, -1)
			var seat := c + Vector2i(0, 1)
			if not model.in_bounds(clerk) or model.cell_solid(clerk) or not model.in_bounds(seat):
				continue
			if not model.object_at(clerk).is_empty():
				continue
			var a := Actor.new()
			a.actor_id = "ambient_clerk"
			container.add_child(a)
			a.setup(str(sprites[n % sprites.size()]), model, Vector2(clerk), "sw")
			if Assets.has_anim(a.sprite_id, "work"):
				a.idle_anim = "work"
				a.set_anim("work")
			a._frame = rng.randi_range(0, 1)
			desks.append({"clerk": clerk, "seat": seat, "busy": false, "actor": a})
			n += 1


func _free_desk() -> int:
	var free: Array = []
	for i in desks.size():
		if not bool((desks[i] as Dictionary)["busy"]):
			free.append(i)
	if free.is_empty():
		return -1
	return int(free[rng.randi_range(0, free.size() - 1)])


# ---------------------------------------------------------------- staff
func _open_cells(rect: Array) -> Array:
	var out: Array = []
	var x0 := 0
	var y0 := 0
	var x1 := model.size.x - 1
	var y1 := model.size.y - 1
	if rect.size() == 4:
		x0 = int(rect[0]); y0 = int(rect[1]); x1 = int(rect[2]); y1 = int(rect[3])
	for y in range(y0, y1 + 1):
		for x in range(x0, x1 + 1):
			var c := Vector2i(x, y)
			if model.walkable(c) and model.object_at(c).is_empty():
				out.append(c)
	return out


func _build_staff() -> void:
	for s: Variant in cfg.get("staff", []):
		if not (s is Dictionary):
			continue
		var sd: Dictionary = s
		var night := Clock.is_night()
		if (night and not bool(sd.get("night", false)) and not bool(sd.get("always", false))) or (not night and bool(sd.get("night", false))):
			continue
		var cells := _open_cells(sd.get("rect", []))
		if cells.is_empty():
			continue
		for i in int(sd.get("count", 1)):
			var w := Wanderer.new()
			w.actor_id = "ambient_staff"
			w.cells = cells
			w.rng = rng
			var pz: Array = sd.get("pause", [1.5, 5.0])
			w.pause_range = Vector2(float(pz[0]), float(pz[1]))
			container.add_child(w)
			w.setup(str(sd.get("sprite", "chr_clerk_grey")), model, Vector2(cells[rng.randi_range(0, cells.size() - 1)]),
				["sw", "se", "nw", "ne"][rng.randi_range(0, 3)])
			w.speed = rng.randf_range(1.6, 2.4)
			w._wait = rng.randf_range(0.0, 3.0)


## Souls the player stamped DEFERRED drift about this area for good (area key "residents": [x0, y0, x1, y1]).
## Or, with "resident_cells": [[x0, y0, x1, y1], ...], each Resident is locked in its own cell (round-robin).
func _build_residents() -> void:
	var rc: Variant = cfg.get("resident_cells")
	var r: Variant = cfg.get("residents")
	if not (rc is Array) and not (r is Array):
		return
	var list := GameState.residents()
	for i in list.size():
		var cid: String = str(list[i])
		var rect: Array = (rc as Array)[i % (rc as Array).size()] if rc is Array and not (rc as Array).is_empty() else (r as Array)
		var cells := _open_cells(rect)
		if cells.is_empty():
			continue
		_spawn_resident(cid, cells)


func _spawn_resident(cid: String, cells: Array) -> void:
	var w := Wanderer.new()
	w.actor_id = "resident_" + str(cid)
	w.cells = cells
	w.rng = rng
	w.pause_range = Vector2(4.0, 10.0)
	container.add_child(w)
	var c := Content.case(str(cid))
	var seed_v := int((c.get("portrait", {}) as Dictionary).get("seed", str(cid).hash()))
	w.setup("chr_soul_%d" % (absi(seed_v) % 4), model, Vector2(cells[rng.randi_range(0, cells.size() - 1)]), "sw")
	w.speed = 0.9
	w.modulate = Color(0.8, 0.72, 1.0, 0.85) # a faint Purgatory tint marks the Residents


# ---------------------------------------------------------------- soul flows
func _process(delta: float) -> void:
	var flows: Array = cfg.get("flows", [])
	for i in flows.size():
		_flow_t[i] = float(_flow_t[i]) - delta
		if float(_flow_t[i]) <= 0.0:
			var ev: Array = (flows[i] as Dictionary).get("every", [3.0, 6.0])
			_flow_t[i] = rng.randf_range(float(ev[0]), float(ev[1]))
			_spawn_flow(i, false)


func _pick(list: Variant) -> Vector2i:
	if list is Array and not (list as Array).is_empty():
		var arr: Array = list
		var first: Variant = arr[0]
		if first is Array:
			return JsonUtil.to_vec2i(arr[rng.randi_range(0, arr.size() - 1)])
		return JsonUtil.to_vec2i(arr)
	return Vector2i(-1, -1)


func _soul_doors() -> Array:
	var out: Array = []
	for o: Variant in model.objects:
		if o is Dictionary and str((o as Dictionary).get("type", "")) == "soul_door":
			out.append(o)
	return out


func _new_soul(at: Vector2i) -> Actor:
	var w := Actor.new()
	w.actor_id = "ambient_soul"
	container.add_child(w)
	w.setup("chr_soul_%d" % rng.randi_range(0, 3), model, Vector2(at), "ne")
	w.speed = rng.randf_range(1.4, 2.1)
	w.use_soul_nav = true
	w.modulate.a = 0.0
	w.create_tween().tween_property(w, "modulate:a", 1.0, FADE_S)
	walkers.append(w)
	return w


func _vanish(w: Actor) -> void:
	if not is_instance_valid(w):
		return
	walkers.erase(w)
	var tw := w.create_tween()
	tw.tween_property(w, "modulate:a", 0.0, FADE_S)
	tw.tween_callback(w.queue_free)


func _spawn_flow(i: int, prewarm: bool) -> void:
	if walkers.size() >= _max_walkers:
		return
	var f: Dictionary = (cfg.get("flows", []) as Array)[i]
	if Clock.is_night() and not bool(f.get("night", false)):
		return # the queue sleeps
	var start := _pick(f.get("from", []))
	if start.x < 0:
		return
	match str(f.get("kind", "pass")):
		"pass":
			var goal := _pick(f.get("to", []))
			var p := model.soul_path(start, goal)
			if p.size() < 2:
				return
			var at := p[rng.randi_range(0, p.size() / 2)] if prewarm else start
			var w := _new_soul(at)
			if prewarm:
				p = model.soul_path(at, goal)
			w.arrived.connect(func() -> void: _vanish(w), CONNECT_ONE_SHOT)
			w.walk_path(p)
		"judged":
			var di := _free_desk()
			if di < 0:
				return
			var d: Dictionary = desks[di]
			var seat: Vector2i = d["seat"]
			var p := model.soul_path(start, seat)
			if p.size() < 2:
				return
			d["busy"] = true
			var w := _new_soul(seat if prewarm else start)
			if prewarm:
				_judge(w, di, float(f.get("hell_share", 0.6)))
				return
			w.arrived.connect(func() -> void: _judge(w, di, float(f.get("hell_share", 0.6))), CONNECT_ONE_SHOT)
			w.walk_path(p)


## Soul sits at a desk while the clerk works, then leaves by the Gilt or Ember door.
func _judge(w: Actor, di: int, hell_share: float) -> void:
	if not is_instance_valid(w):
		return
	var d: Dictionary = desks[di]
	w.face_towards(Vector2(d["clerk"] as Vector2i))
	var clerk: Actor = d["actor"]
	var t := get_tree().create_timer(rng.randf_range(4.0, 9.0))
	t.timeout.connect(func() -> void:
		d["busy"] = false
		if not is_instance_valid(w):
			return
		if is_instance_valid(clerk):
			clerk.face_towards(Vector2(d["seat"] as Vector2i))
		var doors := _soul_doors()
		if doors.is_empty():
			_vanish(w)
			return
		var want := "hell" if rng.randf() < hell_share else "heaven"
		var door: Dictionary = doors[0]
		for o: Dictionary in doors:
			if str(o.get("verdict", "")) == want:
				door = o
		var p := model.soul_path(w.cell(), JsonUtil.to_vec2i(door.get("cell")))
		if p.is_empty():
			_vanish(w)
			return
		w.arrived.connect(func() -> void: _vanish(w), CONNECT_ONE_SHOT)
		w.walk_path(p))


## A staff member who strolls between open cells, pausing in between.
class Wanderer:
	extends Actor
	var cells: Array = []
	var rng: RandomNumberGenerator
	var pause_range := Vector2(1.5, 5.0)
	var _wait := 0.0

	func _process(delta: float) -> void:
		if path.is_empty():
			_wait -= delta
			if _wait <= 0.0 and not cells.is_empty():
				_wait = rng.randf_range(pause_range.x, pause_range.y)
				var c: Vector2i = cells[rng.randi_range(0, cells.size() - 1)]
				if Vector2(c - cell()).length() < 9.0:
					go_to(c)
		super._process(delta)
